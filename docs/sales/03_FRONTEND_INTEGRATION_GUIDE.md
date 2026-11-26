# 03. Guía de Integración Frontend — Ventas (`commerce/sales`)

Esta guía técnica está dirigida a desarrolladores frontend (Angular 21 / PrimeNG 21 y React PWA) para la integración limpia, reactiva y desacoplada del módulo de **Ventas**.

---

## 📦 1. Modelos e Interfaces TypeScript

Asegurar la siguiente estructura en `src/app/features/commerce/sales/models/sale.model.ts`:

```typescript
export interface SaleItem {
  id: string;
  sale_id: string;
  product_id: string;
  item_number?: number | null;
  code?: string | null;
  product_name: string;
  variant_name?: string | null;
  quantity: number;
  unit_price: number;
  unit_cost: number;
  total_price: number;
  net_margin: number;
}

export interface SaleItemCreatePayload {
  product_id: string;
  quantity: number;
  unit_price: number;
}

export interface Sale {
  id: string;
  sale_number: number;              // Entero secuencial atómico (#1, #2, #29...)
  sheet_sale_id?: number | null;
  sale_date: string;
  customer_name: string;
  customer_phone?: string | null;
  channel_id?: string | null;
  channel: string;
  channel_name?: string | null;      // Nombre descriptivo resuelto por el backend
  payment_method: string;            // 'QR' | 'CASH' | 'TRANSFER' | 'COURTESY'
  payment_status: string;            // 'COLLECTED' | 'PENDING' | 'COURTESY'
  delivery_modality: string;         // 'FREE_MEETING_POINT' | 'HOME_DELIVERY' | 'TERMINAL_BUS' | 'STORE_PICKUP'
  delivery_address?: string | null;
  delivery_cost: number;
  delivery_cost_paid_by: string;     // 'FREE' | 'CUSTOMER' | 'STORE'
  delivery_status: string;           // 'DELIVERED' | 'PENDING' (Opción 2 Simplificada)
  amount_tendered?: number | null;   // Efectivo entregado por el cliente
  change_given?: number | null;      // Vuelto entregado
  total_collected: number;
  total_cost: number;
  net_profit: number;
  currency: string;
  observations?: string | null;
  items?: SaleItem[];
  created_at?: string | null;
  updated_at?: string | null;
  created_by_id?: string | null;
  updated_by_id?: string | null;
}

export interface AvailableProductForSale {
  id: string;
  master_product_id: string;
  item_number?: number | null;      // Correlativo #54
  code?: string | null;
  name: string;
  variant_name?: string | null;
  batch_code?: string | null;
  batch_name?: string | null;
  available_quantity: number;       // Existencia física vendible
  published_price: number;          // Precio oficial de venta
  minimum_price: number;            // Piso mínimo de regateo
  official_price: number;           // Referencia promedio de mercado
  discount_margin: number;          // Margen de descuento disponible
  currency: string;
  image_url?: string | null;
}

export interface SaleCreatePayload {
  sale_number?: number | null;
  sale_date?: string | null;
  customer_name: string;
  customer_phone?: string | null;
  channel_id?: string | null;
  channel: string;
  payment_method: string;
  payment_status: string;
  delivery_modality: string;
  delivery_address?: string | null;
  delivery_cost?: number;
  delivery_cost_paid_by?: string;
  delivery_status?: string;
  amount_tendered?: number | null;
  change_given?: number | null;
  total_collected?: number | null;
  currency?: string;
  observations?: string | null;
  allow_below_minimum?: boolean;
  items: SaleItemCreatePayload[];
}
```

---

## 🔌 2. Endpoints y Servicio Angular (`SaleService`)

```typescript
// src/app/features/commerce/sales/services/sale.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import { Sale, SaleCreatePayload, AvailableProductForSale } from '../models/sale.model';

@Injectable({ providedIn: 'root' })
export class SaleService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/api/commerce/sales`;

  // Listado paginado con búsqueda
  getSales(params: { offset?: number; limit?: number; search?: string; channel?: string; payment_status?: string; delivery_status?: string }): Observable<Sale[]> {
    let httpParams = new HttpParams();
    if (params.offset !== undefined) httpParams = httpParams.set('offset', params.offset);
    if (params.limit !== undefined) httpParams = httpParams.set('limit', params.limit);
    if (params.search?.trim()) httpParams = httpParams.set('search', params.search.trim());
    if (params.channel) httpParams = httpParams.set('channel', params.channel);
    if (params.payment_status) httpParams = httpParams.set('payment_status', params.payment_status);
    if (params.delivery_status) httpParams = httpParams.set('delivery_status', params.delivery_status);
    return this.http.get<Sale[]>(this.baseUrl, { params: httpParams });
  }

  // Conteo total para paginación
  getCount(search?: string): Observable<{ total: number }> {
    let httpParams = new HttpParams();
    if (search?.trim()) httpParams = httpParams.set('search', search.trim());
    return this.http.get<{ total: number }>(`${this.baseUrl}/count`, { params: httpParams });
  }

  // Catálogo POS Desacoplado: Búsqueda reactiva de productos disponibles
  getAvailableProducts(search?: string, limit: number = 50): Observable<AvailableProductForSale[]> {
    let httpParams = new HttpParams().set('limit', limit);
    if (search?.trim()) httpParams = httpParams.set('search', search.trim());
    return this.http.get<AvailableProductForSale[]>(`${this.baseUrl}/available-products`, { params: httpParams });
  }

  // Creación atómica
  create(payload: SaleCreatePayload): Observable<Sale> {
    return this.http.post<Sale>(this.baseUrl, payload);
  }
}
```

---

## ⚡ 3. Implementación de la Opción C (Búsqueda Híbrida en `SaleDrawerComponent`)

La Opción C combina la carga inicial rápida con búsqueda remota inteligente con *debounce*:

```typescript
// En SaleDrawerComponent
import { Subject, debounceTime, distinctUntilChanged, switchMap, catchError, of, finalize } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

export class SaleDrawerComponent implements OnInit {
  private readonly saleService = inject(SaleService);

  readonly initialProducts = signal<AvailableProductForSale[]>([]);
  readonly displayProducts = signal<AvailableProductForSale[]>([]);
  readonly isSearchingProducts = signal<boolean>(false);
  readonly selectedProductDetails = signal<AvailableProductForSale | null>(null);

  private readonly searchProduct$ = new Subject<string>();

  constructor() {
    // Configuración del debounce de búsqueda remota (300 ms)
    this.searchProduct$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(query => {
        const term = query.trim();
        if (!term) {
          this.isSearchingProducts.set(false);
          this.displayProducts.set(this.initialProducts());
          return of(this.initialProducts());
        }

        this.isSearchingProducts.set(true);
        return this.saleService.getAvailableProducts(term, 30).pipe(
          catchError(() => of([])),
          finalize(() => this.isSearchingProducts.set(false))
        );
      }),
      takeUntilDestroyed()
    ).subscribe(products => {
      this.displayProducts.set(products);
    });
  }

  // Carga inicial al abrir el drawer
  loadInitialProducts(): void {
    this.isSearchingProducts.set(true);
    this.saleService.getAvailableProducts('', 50).subscribe({
      next: prods => {
        this.initialProducts.set(prods);
        this.displayProducts.set(prods);
        this.isSearchingProducts.set(false);
      },
      error: () => this.isSearchingProducts.set(false)
    });
  }

  onProductFilter(event: { filter: string }): void {
    this.searchProduct$.next(event.filter || '');
  }

  onProductSelectedForAdd(productId: string | null): void {
    this.selectedProductIdToAdd.set(productId);
    if (!productId) {
      this.selectedProductDetails.set(null);
      this.itemPriceToAdd.set(0);
      return;
    }

    const prod = this.displayProducts().find(p => p.id === productId);
    if (prod) {
      this.selectedProductDetails.set(prod);
      // Autocompletar con el Precio Publicado
      this.itemPriceToAdd.set(prod.published_price || 0);
    }
  }
}
```

---

## 🎨 4. Template Visual de Cotización y Regateo (Tri-Precio)

Dentro de `sale-drawer.component.html`:

```html
<!-- Barra Visual del Tri-Precio al seleccionar un producto -->
@if (selectedProductDetails(); as prod) {
  <div class="sm:col-span-12 p-3 bg-blue-50/80 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/60 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs shadow-2xs mt-1">
    <div class="flex flex-wrap items-center gap-3">
      <!-- Precio Publicado -->
      <span class="text-gray-700 dark:text-gray-300">
        P. Publicado: <strong class="text-blue-700 dark:text-blue-400 font-mono text-sm">{{ prod.published_price | number:'1.2-2' }} Bs</strong>
      </span>
      <span class="text-gray-300 dark:text-gray-700">|</span>
      <!-- Piso Mínimo -->
      <span class="text-gray-700 dark:text-gray-300">
        Piso Mínimo: <strong class="text-amber-700 dark:text-amber-400 font-mono text-sm">{{ prod.minimum_price | number:'1.2-2' }} Bs</strong>
      </span>
      <span class="text-gray-300 dark:text-gray-700">|</span>
      <!-- Referencia de Mercado -->
      @if (prod.official_price > 0) {
        <span class="text-gray-500 dark:text-gray-400">
          Ref. Mercado: <del class="font-mono">{{ prod.official_price | number:'1.2-2' }} Bs</del>
        </span>
      }
    </div>

    <!-- Stock y Margen -->
    <div class="flex items-center gap-2">
      <span class="font-bold text-emerald-700 dark:text-emerald-400 font-mono bg-emerald-100 dark:bg-emerald-950/60 px-2 py-0.5 rounded text-[11px]">
        {{ prod.available_quantity }} en almacén
      </span>
      @if (prod.discount_margin > 0) {
        <span class="text-[10px] bg-amber-100 dark:bg-amber-900/40 text-amber-900 dark:text-amber-300 px-2 py-0.5 rounded font-medium">
          Margen rebaja: {{ prod.discount_margin | number:'1.2-2' }} Bs
        </span>
      } @else {
        <span class="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded font-medium">
          Precio Fijo
        </span>
      }
    </div>
  </div>
}
```

---

## 🚚 5. Estados de Logística (Severidad de Tags)

Para la presentación visual en tablas y tarjetas (`SaleListComponent`):

```typescript
getDeliveryStatusSeverity(status: string): 'success' | 'warn' | 'secondary' {
  switch (status) {
    case 'DELIVERED':
      return 'success';   // Verde: Entregado
    case 'PENDING':
      return 'warn';      // Naranja: Pendiente de entrega
    default:
      return 'secondary';
  }
}
```
