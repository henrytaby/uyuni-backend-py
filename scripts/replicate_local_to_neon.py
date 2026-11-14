#!/usr/bin/env python3
"""
Replicate all tables and data from local PostgreSQL to remote Neon PostgreSQL.
Safely handles dependency order, self-referential user FKs, and sequence recalibration.
"""

import psycopg2
from psycopg2 import extras

LOCAL_URL = "postgresql://postgres:postgres@localhost/uyuni_prod"
NEON_URL = (
    "postgresql://neondb_owner:npg_9jMObHTc6tWV@"
    "ep-proud-butterfly-bbrv4ndr-pooler.c-15.us-east-1.aws.neon.tech/uyuni_prod"
    "?sslmode=require&channel_binding=require"
)

TABLES_IN_ORDER = [
    "role",
    "user",
    "user_role",
    "module_group",
    "module",
    "role_module",
    "commerce_category",
    "commerce_channel",
    "commerce_live_basket",
    "commerce_investment_round",
    "commerce_batch",
    "commerce_product_master",
    "commerce_product",
    "commerce_product_master_external_link",
    "commerce_product_master_image",
    "commerce_sale",
    "commerce_sale_item",
    "audit_log",
    "task",
    "user_log_login",
    "user_revoked_token",
]


def replicate():
    print("🚀 Iniciando replicación de Local PostgreSQL -> Neon PostgreSQL...")
    src_conn = psycopg2.connect(LOCAL_URL)
    src_cur = src_conn.cursor()

    dest_conn = psycopg2.connect(NEON_URL)
    dest_cur = dest_conn.cursor()

    try:
        print("🧹 Limpiando tablas previas en destino en orden inverso...")
        for table in reversed(TABLES_IN_ORDER):
            dest_cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = %s AND table_schema = 'public';
                """,
                (table,),
            )
            if dest_cur.fetchone():
                dest_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
        dest_conn.commit()
        print("✨ Tablas limpiadas correctamente.\n")

        for table in TABLES_IN_ORDER:
            # Get columns from destination to ensure exact match
            dest_cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position;
                """,
                (table,),
            )
            cols = [r[0] for r in dest_cur.fetchall()]
            if not cols:
                print(f"⚠️  Tabla {table} no existe en destino. Omitiendo.")
                continue

            quoted_cols = ", ".join(f'"{c}"' for c in cols)
            src_cur.execute(f'SELECT {quoted_cols} FROM "{table}";')
            rows = src_cur.fetchall()
            row_count = len(rows)

            if row_count == 0:
                print(f"ℹ️  {table}: 0 filas en local.")
                continue

            # Serialize dict objects as JSON for psycopg2
            formatted_rows = [
                tuple(extras.Json(v) if isinstance(v, dict) else v for v in row)
                for row in rows
            ]

            # Special handling for 'user' self-references
            if table == "user":
                created_by_idx = cols.index("created_by_id")
                updated_by_idx = cols.index("updated_by_id")
                id_idx = cols.index("id")

                modified_rows = []
                fk_updates = []
                for row in formatted_rows:
                    r_list = list(row)
                    user_id = r_list[id_idx]
                    orig_created_by = r_list[created_by_idx]
                    orig_updated_by = r_list[updated_by_idx]
                    fk_updates.append((orig_created_by, orig_updated_by, user_id))

                    r_list[created_by_idx] = None
                    r_list[updated_by_idx] = None
                    modified_rows.append(tuple(r_list))

                insert_sql = f'INSERT INTO "{table}" ({quoted_cols}) VALUES %s'
                extras.execute_values(
                    dest_cur, insert_sql, modified_rows, page_size=1000
                )

                # Update the self-references now that all user IDs exist
                for created_by, updated_by, uid in fk_updates:
                    dest_cur.execute(
                        """
                        UPDATE "user"
                        SET created_by_id = %s, updated_by_id = %s
                        WHERE id = %s;
                        """,
                        (created_by, updated_by, uid),
                    )
            else:
                insert_sql = f'INSERT INTO "{table}" ({quoted_cols}) VALUES %s'
                extras.execute_values(
                    dest_cur, insert_sql, formatted_rows, page_size=1000
                )

            print(f"✅ {table}: {row_count} filas transferidas.")

        dest_conn.commit()
        print("\n🔄 Recalibrando secuencias en Neon...")

        # Calibrate sequences safely
        dest_cur.execute(
            """
            SELECT setval(
                'commerce_product_master_item_number_seq',
                GREATEST(
                    COALESCE((SELECT MAX(item_number) FROM commerce_product_master), 1),
                    1
                ),
                (SELECT MAX(item_number) FROM commerce_product_master) IS NOT NULL
            );
            """
        )
        seq_val = dest_cur.fetchone()[0]
        print(f"🔢 Secuencia calibrada a: {seq_val}")

        dest_conn.commit()

        # Verification step
        print("\n" + "=" * 65)
        print("📊 VERIFICACIÓN DE CONTEOS ENTRE LOCAL Y NEON")
        print("=" * 65)
        print(f"{'Tabla':<40} {'Local':>8} {'Neon':>8} {'Estado':>8}")
        print("-" * 65)

        all_ok = True
        for table in TABLES_IN_ORDER:
            src_cur.execute(f'SELECT count(*) FROM "{table}";')
            local_cnt = src_cur.fetchone()[0]

            dest_cur.execute(f'SELECT count(*) FROM "{table}";')
            neon_cnt = dest_cur.fetchone()[0]

            status = "OK" if local_cnt == neon_cnt else "MISMATCH"
            if status != "OK":
                all_ok = False
            print(f"{table:<40} {local_cnt:>8} {neon_cnt:>8} {status:>8}")

        print("-" * 65)
        if all_ok:
            print("🎉 ¡TODOS LOS DATOS Y TABLAS FUERON REPLICADOS CON ÉXITO AL 100%!")
        else:
            print("⚠️ Advertencia: Algunos conteos no coinciden.")

    except Exception as e:
        dest_conn.rollback()
        print(f"❌ Error durante la replicación: {e}")
        raise
    finally:
        src_conn.close()
        dest_conn.close()


if __name__ == "__main__":
    replicate()
