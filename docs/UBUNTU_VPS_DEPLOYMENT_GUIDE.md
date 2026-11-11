# Guía de Instalación y Despliegue en Servidor Ubuntu (VPS) — Uyuni Backend

Esta guía proporciona el procedimiento completo, paso a paso y listo para producción, para desplegar el backend **Uyuni / Nova Box Bolivia** en un servidor privado virtual (**VPS**) con **Ubuntu 22.04 LTS** o **Ubuntu 24.04 LTS**.

---

## 🏗️ Arquitectura de Producción

En el servidor VPS, los componentes interactúan de la siguiente manera:

```mermaid
flowchart TD
    Internet["Internet (Clientes / Frontends)"] -->|HTTPS 443| Nginx["Nginx (Reverse Proxy + SSL Let's Encrypt)"]
    Nginx -->|HTTP 8000| Uvicorn["Uvicorn ASGI Workers (Systemd Daemon)"]
    Uvicorn -->|SQLModel / SQLAlchemy| Postgres[("PostgreSQL Local 5432")]
    
    subgraph Host ["Servidor Ubuntu VPS (Linux)"]
        Nginx
        Uvicorn
        Postgres
        Systemd["Systemd Service uyuni-backend"] -.->|Monitorea y reinicia| Uvicorn
    end

    classDef clientNode fill:#f0f9ff,stroke:#00b4d8,stroke-width:2px,color:#003865,font-weight:bold;
    classDef proxyNode fill:#002b49,stroke:#00c2cb,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef appNode fill:#003865,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef dbNode fill:#004889,stroke:#38bdf8,stroke-width:2.5px,color:#ffffff,font-weight:bold;
    classDef sysNode fill:#f8fafc,stroke:#94a3b8,stroke-width:1.5px,color:#334155;

    class Internet clientNode;
    class Nginx proxyNode;
    class Uvicorn appNode;
    class Postgres dbNode;
    class Systemd sysNode;
```

---

## 📋 Requisitos Previos

1. **VPS:** Mínimo 1 vCPU y 1 GB de RAM (recomendado 2 vCPU y 2 GB de RAM o activar swap de 2 GB).
2. **Sistema Operativo:** Ubuntu 22.04 LTS o 24.04 LTS con acceso `sudo` o `root`.
3. **Dominio o Subdominio (Opcional pero recomendado para SSL):** Un registro DNS tipo `A` que apunte la IP pública de tu VPS a tu dominio (ej: `api.novabox.bo` o `api.tudominio.com`). Si no tienes dominio, puedes usar la IP pública temporalmente.

---

## 🚀 Paso a Paso de Instalación

### Paso 1: Actualizar el Sistema e Instalar Python 3.14

Conéctate por SSH a tu VPS:
```bash
ssh root@IP_DE_TU_VPS
```

#### 1.1 Actualizar paquetes base y dependencias del sistema:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget ufw build-essential libpq-dev \
                    software-properties-common ca-certificates
```

#### 1.2 Instalar Python 3.14 (vía PPA oficial deadsnakes):
Por defecto, Ubuntu 22.04 incluye Python 3.10 y Ubuntu 24.04 incluye Python 3.12. Para instalar **Python 3.14** (utilizado por Uyuni Backend), agregamos el repositorio oficial mantenido por el equipo de Python para Ubuntu:

```bash
# 1. Agregar el repositorio PPA deadsnakes
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 2. Instalar el intérprete Python 3.14, soporte para virtualenv y cabeceras de desarrollo
sudo apt install -y python3.14 python3.14-venv python3.14-dev python3-pip

# 3. Comprobar que Python 3.14 esté correctamente instalado
python3.14 --version
# Salida esperada: Python 3.14.x (ej: Python 3.14.6)
```

> [!TIP]
> **Compatibilidad de Versiones Menores**: El PPA de `deadsnakes` instala la rama de mantenimiento oficial de Python 3.14 (3.14.6+), garantizando total compatibilidad binaria de C-extensions, SQLModel, Pydantic v2 y FastAPI.

#### 1.3 Configurar memoria Swap (Recomendado para VPS de 1 GB o 2 GB de RAM):
Si tu VPS tiene recursos ajustados, crea un archivo Swap de 2 GB para evitar que el compilador o los workers se queden sin memoria durante la instalación de paquetes:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

### Paso 2: Instalar y Configurar PostgreSQL

1. **Instalar PostgreSQL:**
```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql
```

2. **Crear usuario y base de datos:**
Accede a la consola de PostgreSQL:
```bash
sudo -u postgres psql
```

Ejecuta las siguientes instrucciones SQL (reemplaza `TU_PASSWORD_SUPER_SEGURO` por una contraseña real y guárdala):
```sql
-- 1. Crear usuario con contraseña
CREATE USER uyuni_user WITH PASSWORD 'TU_PASSWORD_SUPER_SEGURO';

-- 2. Crear base de datos de producción
CREATE DATABASE uyuni_prod OWNER uyuni_user;

-- 3. Otorgar privilegios
GRANT ALL PRIVILEGES ON DATABASE uyuni_prod TO uyuni_user;

-- 4. En PostgreSQL 15+, otorgar permisos sobre el esquema public
\c uyuni_prod
GRANT ALL ON SCHEMA public TO uyuni_user;

-- Salir
\q
```

---

### Paso 3: Crear Usuario de Sistema y Clonar el Repositorio

Por seguridad, nunca ejecutes aplicaciones web como usuario `root`. Crearemos un usuario dedicado llamado `deploy`:

```bash
# Crear usuario de sistema deploy
sudo adduser --disabled-password --gecos "" deploy

# Dar permisos a la carpeta /opt/uyuni
sudo mkdir -p /opt/uyuni
sudo chown -R deploy:deploy /opt/uyuni
```

Ahora cambia al usuario `deploy` y clona tu repositorio:
```bash
sudo -u deploy -i
cd /opt/uyuni

# Clonar el proyecto (o copiarlo mediante rsync/git)
git clone https://github.com/TU_USUARIO/uyuni-backend-py.git .
```

---

### Paso 4: Crear el Entorno Virtual con Python 3.14 e Instalar Dependencias

Aún como usuario `deploy` dentro de `/opt/uyuni`:
```bash
# Crear virtualenv asegurando explícitamente el uso del intérprete Python 3.14
python3.14 -m venv venv

# Verificar que el entorno virtual use efectivamente Python 3.14
venv/bin/python --version
# Salida esperada: Python 3.14.x (ej: Python 3.14.6)

# Activar el entorno e instalar requerimientos
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

---

### Paso 5: Configurar Variables de Entorno de Producción (`.env`)

Genera una clave criptográfica segura para JWT:
```bash
openssl rand -hex 32
```
*Copia el valor generado (ej: `8a7b9c0d1e2f3a4b...`).*

Crea el archivo `.env`:
```bash
nano /opt/uyuni/.env
```

Pega la siguiente configuración y ajusta la contraseña de PostgreSQL, el dominio de tu frontend y la clave secreta:

```env
# ==========================================
# Configuración de Base de Datos PostgreSQL
# ==========================================
DATABASE_URL=postgresql://uyuni_user:TU_PASSWORD_SUPER_SEGURO@127.0.0.1:5432/uyuni_prod

# ==========================================
# Seguridad y Autenticación JWT
# ==========================================
SECRET_KEY=PEGA_AQUI_LA_CLAVE_GENERADA_CON_OPENSSL
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Bloqueo por intentos fallidos de inicio de sesión
SECURITY_LOGIN_MAX_ATTEMPTS=5
SECURITY_LOCKOUT_MINUTES=15

# ==========================================
# Configuración de la Aplicación
# ==========================================
PROJECT_NAME="Uyuni Backend - Nova Box"
VERSION="v1"
ENVIRONMENT="production"
PORT=8000
TIME_ZONE=-4

# ==========================================
# CORS (Permitir acceso a tu Frontend Angular y PWA)
# ==========================================
# Agrega aquí las URLs de tus frontends separadas por coma
BACKEND_CORS_ORIGINS=["https://admin.tudominio.com", "https://catalogo.tudominio.com", "http://localhost:4200"]

# ==========================================
# Auditoría y Logs
# ==========================================
ENABLE_ACCESS_AUDIT=True
ENABLE_DATA_AUDIT=True
ENABLE_ACCESS_LOGS=True
ACCESS_LOGS_ONLY_ERRORS=True
AUDIT_EXCLUDED_PATHS='["/docs", "/redoc", "/openapi.json", "GET:/health", "/"]'
AUDIT_LOG_EXCLUDE_STATUS_CODES='[404]'
AUDIT_LOG_INCLUDED_METHODS='["POST", "PUT", "PATCH", "DELETE"]'
```
Guarda con `Ctrl + O`, `Enter` y sal con `Ctrl + X`.

Protege el archivo `.env` para que solo el usuario `deploy` pueda leerlo:
```bash
chmod 600 /opt/uyuni/.env
```

---

### Paso 6: Ejecutar Migraciones de Base de Datos

Ejecuta Alembic para crear todas las tablas en la base de datos limpia de PostgreSQL:
```bash
venv/bin/alembic upgrade head
```

#### Crear el Superusuario Inicial (`admin`):
Crea el script de seed para dar de alta al administrador:
```bash
venv/bin/python -c '
from sqlmodel import Session, create_engine, select
from app.core.config import settings
from app.models.user import User
from app.auth.utils import get_password_hash

engine = create_engine(str(settings.DATABASE_URL))
with Session(engine) as s:
    existing = s.exec(select(User).where(User.username == "admin")).first()
    if not existing:
        admin = User(
            username="admin",
            email="admin@novabox.bo",
            password_hash=get_password_hash("PasswordSuperSeguro2026!"),
            is_superuser=True,
            is_active=True
        )
        s.add(admin)
        s.commit()
        print("✅ Superusuario admin creado con éxito!")
    else:
        print("ℹ️ El usuario admin ya existe.")
'
```

Sal de la sesión del usuario `deploy` para volver a `root`:
```bash
exit
```

---

### Paso 7: Configurar Systemd como Demonio de Producción

Crearemos un servicio en Systemd para que FastAPI se ejecute automáticamente, reinicie ante cualquier fallo y levante al encender el VPS.

Crea el archivo de servicio:
```bash
sudo nano /etc/systemd/system/uyuni-backend.service
```

Pega la siguiente configuración:

```ini
[Unit]
Description=Uyuni FastAPI Backend Service (Nova Box)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/opt/uyuni
EnvironmentFile=/opt/uyuni/.env
ExecStart=/opt/uyuni/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 3 --loop uvloop --http httptools
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Habilita y arranca el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable uyuni-backend
sudo systemctl start uyuni-backend
```

Verifica que esté corriendo correctamente:
```bash
sudo systemctl status uyuni-backend
```
*(Debe mostrar `active (running)` con color verde).*

---

### Paso 8: Instalar y Configurar Nginx (Reverse Proxy)

1. **Instalar Nginx:**
```bash
sudo apt install -y nginx
sudo systemctl enable --now nginx
```

2. **Crear archivo de configuración del sitio:**
```bash
sudo nano /etc/nginx/sites-available/uyuni-backend
```

Pega la siguiente configuración (reemplaza `api.tudominio.com` por tu dominio real o por la IP del servidor):

```nginx
server {
    listen 80;
    server_name api.tudominio.com;

    # Tamaño máximo de subida para fotos WebP y comprobantes
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # Forwarding de headers de cliente
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Soporte para WebSockets
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts para transacciones y sincronizaciones
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

3. **Habilitar el sitio y reiniciar Nginx:**
```bash
sudo ln -sf /etc/nginx/sites-available/uyuni-backend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

### Paso 9: Firewall (UFW) y Certificado SSL Gratuito (Let's Encrypt)

1. **Configurar el Firewall UFW:**
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```
*(Confirma con `y` al activar).*

2. **Obtener Certificado SSL Gratuito:**
Instala Certbot y genera el certificado:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.tudominio.com
```
*Sigue las instrucciones en pantalla ingresando tu correo electrónico. Certbot configurará automáticamente la redirección HTTPS permanente.*

3. **Verificar la renovación automática:**
```bash
sudo certbot renew --dry-run
```

---

### Paso 10: Script de Actualización Rápida en Producción (`deploy.sh`)

Para que actualizar el backend en el VPS sea cuestión de un solo comando en el futuro, crearemos un script de deploy:

```bash
sudo nano /opt/uyuni/deploy.sh
```

Pega el siguiente contenido:

```bash
#!/bin/bash
set -e

echo "🚀 Iniciando despliegue de Uyuni Backend..."
cd /opt/uyuni

echo "📥 Descargando últimos cambios de Git..."
git pull origin main

echo "📦 Actualizando dependencias..."
venv/bin/pip install -r requirements.txt

echo "🔄 Ejecutando migraciones de base de datos..."
venv/bin/alembic upgrade head

echo "♻️ Reiniciando servicio FastAPI..."
sudo systemctl restart uyuni-backend

echo "✅ Despliegue completado con éxito!"
sudo systemctl status uyuni-backend --no-pager
```

Hazlo ejecutable y otorga permiso de sudo sin contraseña a `systemctl restart uyuni-backend` para el usuario `deploy`:
```bash
sudo chmod +x /opt/uyuni/deploy.sh
sudo chown deploy:deploy /opt/uyuni/deploy.sh

# Permitir a deploy reiniciar el servicio sin pedir password
echo "deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart uyuni-backend, /bin/systemctl status uyuni-backend" | sudo tee /etc/sudoers.d/deploy-uyuni
```

A partir de ahora, cada vez que quieras actualizar el backend, solo ejecutas:
```bash
sudo -u deploy /opt/uyuni/deploy.sh
```

---

## 🔍 Comandos Útiles de Monitoreo y Diagnóstico

### Ver logs en tiempo real del backend:
```bash
# Ver últimos 100 logs y seguir en vivo
sudo journalctl -u uyuni-backend -f -n 100
```

### Comprobar estado de los servicios:
```bash
sudo systemctl status uyuni-backend
sudo systemctl status nginx
sudo systemctl status postgresql
```

### Reiniciar servicios:
```bash
sudo systemctl restart uyuni-backend
sudo systemctl reload nginx
```

### Probar conexión local:
```bash
curl -I http://127.0.0.1:8000/
```

¡Listo! Tu backend está completamente configurado, securizado con SSL, demonizado con reinicio automático y listo para atender a tus frontends en producción.

