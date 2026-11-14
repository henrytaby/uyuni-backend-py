# 🤖 Guía Técnica: Asistente de IA Comercial (Uyuni ERP)

Documentación oficial de arquitectura, integración y especificación de endpoints para desarrolladores Backend y Frontend (Angular 21 + PrimeNG).

---

## 📌 1. Visión General y Arquitectura

El Asistente Comercial es un motor conversacional conectado directamente a la base de datos de inventario y fichas maestras de Uyuni ERP. Permite a operadores y vendedores consultar existencias físicas en tiempo real, especificaciones técnicas y precios de catálogo sin alucinaciones.

```
[Usuario / Operador en Frontend]
                │
                ▼ POST /api/commerce/assistant/chat
┌──────────────────────────────────────────────────────────────┐
│  CommerceAssistantService                                    │
│  1. Extracción de términos clave (ignora stopwords)          │
│  2. Búsqueda SQL en commerce_product_master                  │
│  3. Cálculo de stock en vivo con get_stock_summary()         │
│  4. Partición estructurada: Disponibles vs Agotados          │
│  5. Construcción de Prompt con Ingeniería de Contexto        │
│  6. Invocación a LlmProvider (Groq ⚡ / Mistral 🛡️ / Fallback)│
└──────────────────────────────────────────────────────────────┘
                │
                ▼ JSON Response
[Respuesta comercial fluida + Matched Products estructurados]
```

---

## 🌐 2. Endpoints de la API

Prefijo base: `/api/commerce/assistant`

### A. Chat con el Asistente
* **Método:** `POST`
* **Ruta:** `/api/commerce/assistant/chat`
* **Autenticación:** Requiere `Authorization: Bearer <JWT_TOKEN>` (Permiso READ en módulo `commerce`).
* **Content-Type:** `application/json`

#### Request Body (`ChatAssistantRequest`)

```json
{
  "message": "¿Tenemos cargador de celular en stock y cuánto cuesta?",
  "history": [
    { "role": "user", "content": "Hola" },
    { "role": "assistant", "content": "¡Hola! ¿En qué producto te ayudo hoy?" }
  ],
  "provider": "groq",
  "model": "openai/gpt-oss-120b",
  "include_stock_data": true
}
```

##### Detalle de Parámetros

| Parámetro | Tipo | Requerido | Default | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| **`message`** | `string` | **SÍ** | — | **La pregunta del usuario.** Texto que escribe el operador en el input del chat (1 a 2000 caracteres). Ej: `"¿Tenemos cargador tipo C?"` o `"¿Cuántos productos en total tenemos en stock?"`. |
| **`history`** | `array` | No | `[]` | **Memoria conversacional.** Lista de mensajes previos `[{ "role": "user"\|"assistant", "content": "..." }]`. Permite que la IA recuerde el contexto. *El backend optimiza automáticamente recortando a los últimos 8 mensajes.* |
| **`provider`** | `string` | No | `null` | **Selector de IA.** Permite sobrescribir el proveedor para esta consulta puntual (`"groq"`, `"mistral"`, `"gemini"`). Si es `null` o se omite, usa `AI_DEFAULT_PROVIDER` del `.env`. |
| **`model`** | `string` | No | `null` | **Selector de modelo.** Permite forzar un modelo específico (ej: `"openai/gpt-oss-120b"` en Groq o `"ministral-8b-latest"` en Mistral). Si es `null`, usa el por defecto del `.env`. |
| **`include_stock_data`** | `boolean` | No | `true` | **Interruptor de inventario.** Si es `true`, busca en la BD de productos y extrae existencias físicas reales. Si es `false`, responde consultas generales sin tocar la BD. |

---

#### Response Body (`ChatAssistantResponse`)

```json
{
  "reply": "## Productos disponibles en stock\n\n| Catálogo # | Producto | Stock | P. Publicado (Venta) | Piso Regateo | P. Lista (Mercado) |\n|---|---|---|---|---|---|\n| #49 | Nanami Estación de carga 3 en 1 USB C 30W | 1 unid. | **180.00 BOB** | **140.00 BOB** | 220.00 BOB |\n\n> **Nota comercial:** Precio oficial publicado de 180 BOB. Si el cliente pide rebaja, tienes un margen de 40 BOB hasta el piso de 140 BOB. Frente al mercado local (220 BOB), el cliente ahorra 40 BOB.",
  "provider_used": "groq",
  "model_used": "openai/gpt-oss-120b",
  "matched_products": [
    {
      "item_number": 49,
      "name": "Nanami Estación de carga 3 en 1 USB C de 30 W para múltiples dispositivos",
      "brand": "HM730CCS",
      "model": null,
      "available_stock": 1,
      "sold_stock": 0,
      "official_price": 220.0,
      "published_price": 180.0,
      "minimum_price": 140.0,
      "currency": "BOB",
      "features": "Base de carga múltiple que permite cargar simultáneamente un teléfono...",
      "description": "Cargador para teléfono reloj y audífonos."
    }
  ],
  "fallback_occurred": false
}
```

##### Detalle de Campos de Respuesta

| Campo | Tipo | Utilidad para el Frontend |
| :--- | :--- | :--- |
| **`reply`** | `string` | Respuesta final generada en Markdown lista para pintar en la burbuja de chat. |
| **`provider_used`** | `string` | Identifica qué proveedor resolvió la consulta (`"groq"` o `"mistral"`). Útil para mostrar un badge como `"⚡ Groq"`. |
| **`model_used`** | `string` | Modelo exacto ejecutado (`"openai/gpt-oss-120b"`). |
| **`matched_products`** | `array` | **Clave para UI/UX:** Lista estructurada de las fichas maestras encontradas en BD con stock real y precios. El frontend puede pintar debajo de la respuesta tarjetas de producto con botón directo a *"Crear Venta"* o *"Ver Ficha"*. |
| **`fallback_occurred`**| `boolean` | Indica si el proveedor primario falló y se activó el respaldo automáticamente sin error para el usuario. |

---

### B. Consulta de Proveedores Activos
* **Método:** `GET`
* **Ruta:** `/api/commerce/assistant/providers`
* **Response:**
  ```json
  {
    "default_provider": "groq",
    "configured_providers": ["groq", "mistral"],
    "all_providers": ["groq", "mistral", "gemini"]
  }
  ```
* **Utilidad Frontend:** Permite poblar un selector en la barra superior del chat con los proveedores que realmente tienen claves válidas en el servidor.

---

## 💻 3. Guía de Integración Frontend (Angular 21 / PrimeNG)

### Modelos TypeScript (`assistant.model.ts`)

```typescript
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface MatchedProduct {
  item_number: number;
  name: string;
  brand?: string;
  model?: string;
  available_stock: number;
  sold_stock: number;
  official_price: number;
  published_price?: number;
  minimum_price: number;
  currency: string;
  features?: string;
  description?: string;
}

export interface ChatAssistantRequest {
  message: string;
  history?: ChatMessage[];
  provider?: string | null;
  model?: string | null;
  include_stock_data?: boolean;
}

export interface ChatAssistantResponse {
  reply: string;
  provider_used: string;
  model_used: string;
  matched_products: MatchedProduct[];
  fallback_occurred: boolean;
}
```

### Servicio Angular (`assistant.service.ts`)

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ChatAssistantRequest, ChatAssistantResponse } from './assistant.model';

@Injectable({ providedIn: 'root' })
export class AssistantService {
  private http = inject(HttpClient);
  private baseUrl = '/api/commerce/assistant';

  sendMessage(payload: ChatAssistantRequest): Observable<ChatAssistantResponse> {
    return this.http.post<ChatAssistantResponse>(`${this.baseUrl}/chat`, payload);
  }

  getProviders(): Observable<{ default_provider: string; configured_providers: string[] }> {
    return this.http.get<any>(`${this.baseUrl}/providers`);
  }
}
```

---

## ⚙️ 4. Variables de Entorno (`.env`)

```bash
# Proveedor principal activo
AI_DEFAULT_PROVIDER=groq
AI_ENABLE_FALLBACK=True

# Groq (Titular - 1.1s)
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b

# Mistral (Respaldo automático - 1.1s)
MISTRAL_API_KEY=...
MISTRAL_MODEL=ministral-8b-latest

# Google Gemini (En la banca - dejar vacío para desactivar)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
```

---

## 💼 5. Estrategia de Tri-Precio y Motor Semántico de la IA

### A. Protocolo de Tri-Precio Comercial
El Copiloto IA asesora al dueño o gerente de mercadería con las 3 capas de precios del ERP:
1. **`P. Publicado` (`published_price`)**: Precio oficial de venta al público en Marketplace o redes sociales. Es el monto principal que el vendedor debe cotizar de entrada al cliente.
2. **`Piso Regateo` (`minimum_price`)**: Límite mínimo de venta autorizado para cerrar el trato si el cliente solicita rebaja.
   - **Margen de Negociación:** $\text{Margen de Rebaja} = \text{P. Publicado} - \text{Piso Regateo}$.
   - **Regla de Precio Fijo:** Si $\text{P. Publicado} == \text{Piso Regateo}$, el asistente indica explícitamente **`Precio Fijo (Sin margen de rebaja)`**.
3. **`P. Lista` (`official_price`)**: Precio de referencia promedio en el mercado local boliviano, utilizado como ancla para argumentar ahorro frente a la competencia.

### B. Motor de Búsqueda Semántica
- **Pool Amplio de 35 Candidatos:** Para búsquedas por categoría o concepto (ej. *"domótica"*, *"accesorios auto"*), el backend consulta hasta **35 productos candidatos** con stock disponible en BD. Esto permite a la IA evaluar un universo completo antes de seleccionar los productos pertinentes.
- **Expansión de Sinónimos:** El sistema mapea familias semánticas (`domotica` $\rightarrow$ `smart home`, `tuya`, `zigbee`, `homekit`, `alexa`, `inteligente`; `auto` $\rightarrow$ `vehículo`, `coche`, `carro`, `automotriz`).
- **Sincronización 1:1 de Tarjetas:** `extract_cited_item_numbers` lee las fichas citadas en el texto o tabla de la IA (`#XX`, `**#XX**`, etc.) y devuelve en `matched_products` **únicamente** los productos aprobados por el modelo, descartando automáticamente cualquier falso positivo del frontend.
