# Themis — inventario, ventas y alertas con microservicios

Webapp para gestionar un catálogo **100% dinámico** de teléfonos, tablets y
accesorios: stock editable, coste/PVP, valor del inventario, ventas con carrito
multi-producto y alertas automáticas por falta de stock. Cada dominio es un
servicio con su propia base de datos y se comunica mediante **eventos
persistentes** (RabbitMQ + patrón transactional outbox). Ningún servicio lee la
base de datos de otro.

## Arquitectura

```
  navegador ──▶ api-gateway + frontend (SPA)  :8080
                │
                ├─ /api/catalog      ─▶ catalog-service      ── product.* ──┐
                ├─ /api/inventory    ─▶ inventory-service    ── stock.* ──┐ │
                ├─ /api/sales        ─▶ sales-service                     │ │
                └─ /api/notifications ─▶ notification-service ◀───────────┘ │
                                                     ▲                      │
                                                     └────── RabbitMQ ◀─────┘
                                                       exchanges products / stock

  sales-service ── HTTP síncrono ──▶ catalog-service (precios/coste)
                └─ HTTP síncrono ──▶ inventory-service (salida de stock)
```

| Servicio | Responsabilidad | Persistencia | Publica | Consume |
| --- | --- | --- | --- | --- |
| `catalog-service` | CRUD dinámico de productos | `postgres-catalog` | `product.*` | — |
| `inventory-service` | Stock, movimientos y umbral | `postgres-inventory` | `stock.*` | `product.*` |
| `sales-service` | Ventas, líneas, ingresos y margen | `postgres-sales` | — | — (llama por HTTP a catálogo e inventario) |
| `notification-service` | Alertas Telegram / WhatsApp | `postgres-notification` | — | `stock.*` |
| `api-gateway` | Enrutado + BFF dashboard + SPA | — | — | — |

Cada servicio tiene **su propio contenedor PostgreSQL**. El desacoplamiento es
estricto: `inventory-service` mantiene una *read model* local construida a partir
de eventos de catálogo, y `notification-service` nunca consulta inventario.

## Catálogo dinámico

No hay marcas, modelos ni capacidades hardcodeadas. Cualquier producto se crea
por API/UI con:

`sku` (único), `brand`, `model`, `category` (`phone|tablet|accessory`),
`ram_gb`, `storage_gb`, `color`, `cost_price_eur`, `price_eur`,
`cost_price_usd`, `price_usd`, `threshold`. `ram_gb`/`storage_gb` admiten `0`
para accesorios. Los precios se editan en EUR y USD; cada venta elige la moneda
y los totales se resuelven por moneda sin mezclar importes. Cada producto
admite una imagen opcional (JPG/PNG/WebP) que se puede subir, previsualizar y
eliminar desde el catálogo.

Validaciones en el borde del servicio (Pydantic) y unicidad de SKU en base de
datos (HTTP 409 ante duplicados).

## Semántica de stock y alertas

- Movimientos: `entry` (mercancía), `exit` (venta) y `adjustment` (valor absoluto).
- El stock no puede quedar negativo: una salida mayor que el stock devuelve 409.
- El evento `stock.depleted` se emite cuando el stock **cruza** el umbral
  (`quantity <= threshold`) y el estado anterior era normal.
- `stock.replenished` se emite al recuperarse. La columna `alert_state`
  (normal/depleted) actúa como **histéresis** y evita alertas repetidas.
- Cada movimiento y evento guarda `correlation_id` para trazabilidad extremo a
  extremo.
- Las ventas usan `POST /stock/batch-exits` y `POST /stock/batch-entries` con un
  `reference_id` (el id de la venta). La tabla de movimientos tiene una
  restricción única `(reference_id, product_id, movement_type)`: reintentar la
  misma venta es idempotente y no descuenta stock dos veces.

### Ventas

`sales-service` orquesta una venta **sin transacción distribuida**:

1. Crea la venta en estado `pending` con una clave de idempotencia y una copia
   del precio/coste de cada producto.
2. Solicita la salida de stock por lotes a inventario con `reference_id=sale_id`.
3. Si inventario confirma, marca la venta como `completed`. Si falta stock
   (409), elimina la venta `pending` y devuelve el error.
4. Un reintento con la misma `idempotency_key` reanuda la venta pendiente o
   devuelve la ya completada.

Cada venta admite varias líneas, precio unitario editable, método de pago
(`cash|card|transfer|other`), moneda (`EUR|USD`), cliente y nota opcionales,
y calcula ingresos, coste y margen. El resumen de ventas (`/sales/summary`)
acepta `?currency=EUR|USD` para no mezclar importes de monedas distintas.

Cada venta admite una factura fiscal opcional (JPG, PNG, WebP o PDF, máx. 10 MB):
`POST/GET/DELETE /sales/{id}/invoice`. La factura se sube tras registrar la
venta y se puede ver, descargar, reemplazar o eliminar desde el detalle de la
venta y del historial.

No incluye impuestos ni devoluciones en esta iteración.

### Contratos

Esquemas versionados en [`contracts/`](contracts):

- `contracts/stock.depleted.schema.json` → `stock.depleted` / `stock.replenished`
- `contracts/product.events.schema.json` → `product.created|updated|deleted`

Payload de `stock.depleted`:

```json
{
  "event_id": "uuid",
  "event_type": "stock.depleted",
  "product_id": "uuid",
  "sku": "IPH-15-128-BLK",
  "product_name": "Apple iPhone 15 128GB Negro",
  "current_stock": 0,
  "threshold": 1,
  "timestamp": "2026-11-19T10:00:00+00:00",
  "correlation_id": "demo-123"
}
```

## Notificaciones (Telegram / WhatsApp)

- Adaptadores aislados: `TelegramChannel` (Bot API) y `WhatsAppChannel`
  (Meta WhatsApp Cloud API). Cambiar de proveedor no toca inventario.
- **Idempotencia** por `event_id` (tabla `processed_events`).
- **Anti-spam** por `(product_id, stock_state)` dentro de una ventana
  configurable (`DEDUPE_WINDOW_SECONDS`, por defecto 300 s).
- **Reintentos** con backoff exponencial para 429/5xx y errores de red
  (`MAX_ATTEMPTS`). Los fallos se registran sin bloquear otros eventos.
- **Dry-run**: si un canal está habilitado pero faltan credenciales, la alerta se
  registra como `dry_run` y no se envía (no necesitas tokens para probar).
- Cola con *dead-letter* (`notification.dead_letter`) para mensajes no
  procesables.

## Arranque rápido

Requisitos: Docker + Docker Compose (o Python 3 + Node 20 para el modo local sin
Docker descrito más abajo).

```sh
cp .env.example .env       # opcional; los valores por defecto funcionan
docker compose up --build
```

- Webapp: <http://localhost:8080>
- RabbitMQ management: <http://localhost:15672> (`guest` / `guest`)
- Gateway health: <http://localhost:8080/health>

Demo automática (crea producto, suma stock, vende hasta 0 y consulta alertas):

```sh
./scripts/demo.sh
```

> Sin credenciales de Telegram/WhatsApp el flujo completo funciona en modo
> dry-run y las alertas quedan visibles en la pestaña «Notificaciones».

### Modo local sin Docker

Si el daemon Docker no está disponible, hay un modo local reproducible:
SQLite aislado por servicio (un fichero por servicio, incluida la base de
ventas) y un bus de eventos HTTP persistente (`services/event-relay`). El código
de dominio y los contratos son los mismos; RabbitMQ y PostgreSQL siguen siendo
el modo de producción en Compose.

```sh
./scripts/run_local.sh          # crea .local/venv, arranca todo y siembra la demo
./scripts/run_local.sh --fresh  # reinicia con bases de datos vacías
./scripts/stop_local.sh         # detiene los procesos
```

La web queda en <http://localhost:8080>. Logs en `.local/logs`.

> No hay Alembic: si cambias el esquema, reinicia con `./scripts/run_local.sh
> --fresh` en local o `docker compose down -v` en Docker.

### Datos de demo

`scripts/seed_demo_inventory.py` carga el inventario real de la tienda usando
solo la API pública (productos dinámicos), con categoría y precios de ejemplo
editables (coste/PVP). La lista contiene **48 productos** (teléfonos, tablets y
accesorios como GPS, UPS y Fire TV) y **68 unidades**; el total de 69 del listado
original no cuadra con la suma de líneas. Los productos a cero disparan
`stock.depleted` durante la carga para poblar el panel de alertas.

```sh
BASE_URL=http://127.0.0.1:8080 python3 scripts/seed_demo_inventory.py
```

### Variables de entorno

Todas documentadas en [`.env.example`](.env.example). Las más relevantes:

| Variable | Uso |
| --- | --- |
| `RABBITMQ_URL` | Conexión AMQP |
| `CATALOG_DATABASE_URL` / `INVENTORY_DATABASE_URL` / `SALES_DATABASE_URL` / `NOTIFICATION_DATABASE_URL` | BD aislada por servicio |
| `SALES_URL` / `CATALOG_URL` / `INVENTORY_URL` | URLs internas usadas por gateway y ventas |
| `PRODUCTS_EXCHANGE` / `STOCK_EXCHANGE` | Nombres de exchanges topic |
| `DEDUPE_WINDOW_SECONDS` / `MAX_ATTEMPTS` | Anti-spam y reintentos |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Canal Telegram |
| `WHATSAPP_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_RECIPIENT` | Canal WhatsApp |
| `GATEWAY_PORT` | Puerto público (8080) |

No hay secretos en el código; los tokens se inyectan por entorno.

## API

A través del gateway (`:8080`), con los prefijos indicados:

### Catálogo → `/api/catalog`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `POST` | `/products` | Crear producto dinámico |
| `GET` | `/products?search=&brand=&limit=&offset=` | Listar/buscar |
| `GET` | `/products/{id}` | Detalle |
| `PATCH` | `/products/{id}` | Actualizar campos |
| `POST` | `/products/{id}/image` | Subir imagen de producto (multipart `file`) |
| `GET` | `/products/{id}/image` | Ver imagen de producto |
| `DELETE` | `/products/{id}/image` | Eliminar imagen de producto |
| `DELETE` | `/products/{id}` | Eliminar (inventario lo desactiva) |

### Inventario → `/api/inventory`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/stock?include_inactive=false` | Estado de stock |
| `GET` | `/stock/{product_id}` | Detalle de stock |
| `GET` | `/stock/{product_id}/movements` | Historial |
| `POST` | `/stock/{product_id}/entries` | `{ "quantity": 5, "note": "..." }` |
| `POST` | `/stock/{product_id}/exits` | `{ "quantity": 5, "note": "..." }` |
| `POST` | `/stock/{product_id}/adjustments` | `{ "quantity": 12, "note": "..." }` (admite `0`) |
| `POST` | `/stock/batch-exits` | `{ "items": [...], "reference_id": "sale-id" }` |
| `POST` | `/stock/batch-entries` | `{ "items": [...], "reference_id": "..." }` |

### Ventas → `/api/sales`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `POST` | `/sales` | Crear venta multi-producto (`idempotency_key` opcional) |
| `GET` | `/sales?limit=100&offset=&status=&search=` | Historial |
| `GET` | `/sales/summary` | Totales de hoy/mes, margen, ranking y serie de 7 días |
| `GET` | `/sales/summary?currency=EUR|USD` | Totales de hoy/mes por moneda |
| `GET` | `/sales/{id}` | Detalle |
| `POST` | `/sales/{id}/invoice` | Subir factura fiscal (multipart `file`) |
| `GET` | `/sales/{id}/invoice` | Ver factura fiscal (inline) |
| `DELETE` | `/sales/{id}/invoice` | Eliminar factura fiscal |

### Notificaciones → `/api/notifications`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/notifications?limit=100&status=` | Historial de envíos |
| `GET` | `/notifications/stats` | Contadores por canal/estado |
| `POST` | `/notifications/test` | Enviar alerta de prueba |

### BFF

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/api/dashboard` | Catálogo + stock + valor de inventario para la SPA |

La cabecera `X-Correlation-ID` se propaga por gateway → servicios → eventos →
logs. Si no se envía, cada borde genera uno.

## Desarrollo local (sin contenedores)

Cada servicio es FastAPI + SQLAlchemy async:

```sh
# terminal 1: infraestructura
docker compose up postgres-catalog postgres-inventory postgres-sales postgres-notification rabbitmq

# terminal 2 (ejemplo catalog)
cd services/catalog
PYTHONPATH=../../libs DATABASE_URL=postgresql+asyncpg://catalog:catalog@localhost:5432/catalog \
  uvicorn app.main:app --reload --port 8001

# frontend con proxy /api -> gateway
cd frontend && npm install && npm run dev
```

La SPA incluye tema claro/oscuro persistente, drawers laterales para stock,
producto y venta, y tablas con cabecera fija.

El `docker-compose.yml` es la vía reproducible y recomendada.

## Pruebas

Pruebas unitarias de la lógica pura (transiciones de umbral, validación de
esquemas de catálogo/ventas y formato de alertas). Requieren las dependencias de
los servicios instaladas en el intérprete:

```sh
./scripts/run_unit_tests.sh
# o indicando un intérprete concreto:
PYTHON=/ruta/al/venv/bin/python ./scripts/run_unit_tests.sh
```

Validación de la infraestructura:

```sh
docker compose config --quiet     # sintaxis y variables
docker compose up --build         # arranque reproducible
```

## Decisiones y límites conocidos

- **Frontend y backend separados:** el backend vive en `services/`, `gateway/` y `libs/`; el frontend en `frontend/`. El gateway solo empaqueta el build estático de Vite para servirlo en producción.
- **Nunca commitees `.env`:** ya está ignorado por `.gitignore`. Copia `.env.example` a `.env` y ajusta contraseñas, tokens, URLs y claves de Supabase antes de levantar.
- **Sin migraciones**: las tablas se crean al arrancar con `create_all` para mantener el ejemplo simple. En producción: Alembic por servicio.
- **Entrega at-least-once**: el outbox garantiza publicación fiable; los
  consumidores son idempotentes. El dispatcher usa `FOR UPDATE SKIP LOCKED`.
- **Sin autenticación**: el gateway es abierto para la demo. Añadir auth/JWT y
  CORS restringido antes de exponerlo.
- **Dry-run por defecto**: sin credenciales no se envían mensajes reales.
- **WhatsApp** implementado contra Meta Cloud API; Twilio requeriría otro
  adaptador (aislado por diseño).
- Las skills del proyecto (`skills/dynamic-phone-inventory-microservices` y
  `skills/messaging-alerts-telegram-whatsapp`) documentan los principios que
  sigue esta implementación.

## Conectar Supabase Storage (imágenes y facturas)

Las imágenes de teléfono y las facturas se suben a Supabase Storage en lugar de disco local.

1. En tu proyecto de Supabase, ve a **Settings → API** y copia:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY`
2. Cópialas a `.env` (está ignorado por `.gitignore`, nunca se sube a GitHub).
3. Crea dos buckets en **Storage**:
   - `product-images` → **Público** (imágenes de teléfonos, URL directa).
   - `sales-invoices` → **Privado** (facturas, solo accesibles mediante URL firmada temporal desde la app).
4. Levanta con Docker:
   ```sh
   cp .env.example .env
   # edita .env con tus valores reales de Supabase
   docker compose up --build
   ```
   O en modo local:
   ```sh
   ./scripts/run_local.sh --fresh
   ```
   `run_local.sh` carga `.env` automáticamente si existe.

Sin `SUPABASE_URL` configurado, el sistema guarda imágenes y facturas en disco local (`media/`) como respaldo.

