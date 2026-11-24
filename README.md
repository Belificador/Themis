# Themis — inventario y ventas en un solo servicio

Webapp para gestionar un catálogo **100% dinámico** de teléfonos, tablets y
accesorios: stock editable, PVP en USD, Ref. BCV y precio Cashea, valor del
inventario, ventas con carrito multi-producto, vendedor, factura fiscal opcional
e imágenes de producto. Todo el backend es **un único servicio FastAPI** con una
sola base de datos; no hay microservicios ni colas de mensajes.

## Arquitectura

```
navegador ──▶ themis-app (FastAPI)
                ├─ /api/catalog       (productos + imágenes)
                ├─ /api/inventory     (stock + movimientos)
                ├─ /api/sales         (ventas + facturas)
                ├─ /api/notifications (alertas de stock)
                ├─ /api/dashboard     (BFF para la SPA)
                └─ /                  (frontend compilado, si existe)

themis-app ──▶ Supabase PostgreSQL (esquema `themis`)
           ──▶ Supabase Storage    (`product-images` público, `sales-invoices` privado)
           ──▶ SQLite local        (fallback sin Supabase)
```

| Componente | Responsabilidad |
| --- | --- |
| `services/app` | API completa: catálogo, inventario, ventas, alertas y BFF |
| `frontend` | SPA React/Vite servida por el propio servicio en producción |
| `libs/egm_common` | Utilidades compartidas (DB async, Supabase Storage, logging) |

En modo local sin Supabase, el servicio usa SQLite (`aiosqlite`) y guarda las
imágenes en disco (`MEDIA_DIR`). Las facturas requieren Supabase Storage porque
se sirven mediante URL firmada temporal.

## Catálogo dinámico

No hay marcas, modelos ni capacidades hardcodeadas. Cualquier producto se crea
por API/UI con:

`sku` (único), `brand`, `model`, `category` (`phone|tablet|accessory`),
`ram_gb`, `ram_virtual_gb`, `storage_gb`, `color`, `price_usd`,
`price_bcv_usd`, `price_cashea_usd`, `camera`, `threshold`.
`ram_gb`/`storage_gb` admiten `0` para accesorios. Los precios son en USD y el
precio de Ref. BCV se recalcula con la tasa oficial/paralelo; cada venta elige
si cobra al PVP o al precio Cashea.

Al crear un producto se crea automáticamente su registro de stock (cantidad 0).
Cada producto admite una imagen opcional (JPG/PNG/WebP) que se puede subir,
previsualizar y eliminar desde el catálogo. Si Supabase está configurado la
imagen se guarda en el bucket público; si no, en `MEDIA_DIR`.

## Semántica de stock y alertas

- Movimientos: `entry` (mercancía), `exit` (venta) y `adjustment` (valor absoluto).
- El stock no puede quedar negativo: una salida mayor que el stock devuelve 409.
- `alert_state` toma `pending|normal|low|depleted` y evita alertas repetidas por
  histéresis: solo se registra un aviso cuando se cruza el umbral.
- Cada movimiento guarda `correlation_id` para trazabilidad.
- La tabla de movimientos tiene una restricción única
  `(reference_id, product_id, movement_type)`: reintentar la misma venta es
  idempotente y no descuenta stock dos veces.

### Ventas

1. Se crea la venta con una copia del precio de cada producto y una clave
   de idempotencia opcional.
2. Se descuenta el stock en la misma transacción; si falta stock se devuelve 409.
3. La venta queda `completed` y se calculan los ingresos.

Cada venta admite varias líneas, precio unitario editable, método de pago
(`cash|card|transfer|other|cashea`), cliente, **vendedor** y nota opcionales.
El resumen (`/api/sales/summary`) devuelve los totales en USD.

La factura fiscal opcional (JPG, PNG, WebP o PDF, máx. 10 MB) se sube tras
registrar la venta y se puede ver o eliminar desde el detalle. La previsualización
usa una URL firmada de 15 minutos (`GET /api/sales/{id}/invoice-url`).

## Arranque rápido

### Docker

```sh
cp .env.example .env       # edita los valores de Supabase si los tienes
docker compose up --build
```

- Webapp + API: <http://localhost:8000>
- Health: <http://localhost:8000/health>

El `Dockerfile` es multi-stage: compila el frontend y lo sirve desde FastAPI.

### Modo local sin Docker

```sh
./scripts/run_local.sh          # crea .local/venv, arranca el servicio y siembra la demo
./scripts/run_local.sh --fresh  # reinicia con base de datos vacía
./scripts/stop_local.sh         # detiene el proceso
```

La web queda en <http://localhost:8000>. Logs en `.local/logs`.

`run_local.sh` carga `.env` automáticamente. Si `SUPABASE_DB_PASSWORD` está
definido usa Supabase PostgreSQL; si no, SQLite en `.local/data`. Fuerza el modo
offline (SQLite + almacenamiento local) con:

```sh
USE_LOCAL_DB=1 ./scripts/run_local.sh --fresh
```

> No hay Alembic: si cambias el esquema, reinicia con `--fresh` en local o
> `docker compose down -v` en Docker.

### Datos de demo

`scripts/seed_demo_inventory.py` carga el inventario real de la tienda usando
solo la API pública. La lista contiene **48 productos** (teléfonos, tablets y
accesorios) y **68 unidades**; los productos a cero generan alertas para poblar
el panel.

```sh
BASE_URL=http://127.0.0.1:8000 python3 scripts/seed_demo_inventory.py
```

Demo rápida (crea producto, suma stock, vende y consulta alertas):

```sh
BASE_URL=http://127.0.0.1:8000 ./scripts/demo.sh
```

## Variables de entorno

Todas documentadas en [`.env.example`](.env.example). Las más relevantes:

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | URL async (por defecto SQLite en Compose) |
| `SUPABASE_DB_PASSWORD` | Si se define, usa Supabase PostgreSQL y esquema `themis` |
| `DB_SCHEMA` | Esquema de Postgres (por defecto `themis`) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase Storage |
| `SUPABASE_BUCKET_PRODUCT_IMAGES` / `SUPABASE_BUCKET_INVOICES` | Buckets |
| `MEDIA_DIR` / `IMAGE_MAX_BYTES` / `INVOICE_MAX_BYTES` | Almacenamiento local y límites |
| `LOG_LEVEL` | Nivel de log |

No hay secretos en el código; se inyectan por entorno. `.env` está ignorado.

## API

Todas las rutas cuelgan del mismo servicio (`:8000`).

### Catálogo → `/api/catalog`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `POST` | `/products` | Crear producto dinámico (crea su stock) |
| `GET` | `/products?search=&brand=&limit=&offset=` | Listar/buscar |
| `GET` | `/products/{id}` | Detalle |
| `PATCH` | `/products/{id}` | Actualizar campos |
| `POST` | `/products/{id}/image` | Subir imagen (multipart `file`) |
| `GET` | `/products/{id}/image` | Ver imagen (redirige a Supabase si aplica) |
| `DELETE` | `/products/{id}/image` | Eliminar imagen |

### Inventario → `/api/inventory`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/stock` | Estado de stock |
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
| `POST` | `/sales` | Crear venta (`vendedor`, `currency`, `idempotency_key` opcionales) |
| `GET` | `/sales?limit=100&offset=&status=&search=` | Historial (busca también por vendedor) |
| `GET` | `/sales/summary` | Totales de hoy/mes, ranking y 7 días en USD |
| `GET` | `/sales/{id}` | Detalle |
| `POST` | `/sales/{id}/invoice` | Subir factura fiscal (multipart `file`) |
| `GET` | `/sales/{id}/invoice-url` | URL firmada temporal de la factura |
| `DELETE` | `/sales/{id}/invoice` | Eliminar factura fiscal |

### Notificaciones → `/api/notifications`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/notifications?limit=100&status=` | Historial de avisos |
| `GET` | `/notifications/stats` | Contadores por canal/estado |
| `POST` | `/notifications/test` | Alerta de prueba (dry-run) |

Sin credenciales externas los avisos se registran como `dry_run`.

### BFF

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/api/dashboard` | Catálogo + stock + valor de inventario para la SPA |

La cabecera `X-Correlation-ID` se propaga a logs. Si no se envía, se genera uno.

## Desarrollo del frontend

```sh
cd frontend && npm install && npm run dev   # proxy /api -> http://localhost:8000
```

La SPA incluye tema claro/oscuro persistente, drawers para stock, producto y
venta, y tablas con cabecera fija. En producción FastAPI sirve `frontend/dist`.

## Pruebas

```sh
./scripts/run_unit_tests.sh
# o con un intérprete concreto:
PYTHON=/ruta/al/venv/bin/python ./scripts/run_unit_tests.sh
```

Validación de infraestructura:

```sh
docker compose config --quiet
docker compose up --build
```

## Despliegue en Render

`render.yaml` define **un solo Web Service** (`themis-app`). El plan gratuito de
Render no incluye Web Services; el más barato es Starter (~7 USD/mes).

1. Crea el Blueprint desde el repo en Render.
2. Rellena en el dashboard las variables marcadas `sync: false`:
   `SUPABASE_DB_PASSWORD`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY`. Opcionalmente `DATABASE_URL`.
3. Build: compila el frontend e instala dependencias Python.
4. Start: `cd services/app && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

La base de datos se crea automáticamente en el esquema `themis` al arrancar.

### Frontend en Vercel (backend separado)

Si prefieres servir el frontend en Vercel y el backend en Render como servicios
independientes:

1. Render: define `CORS_ORIGINS` con el dominio de Vercel
   (`https://tu-app.vercel.app`) y, opcionalmente,
   `CORS_ORIGIN_REGEX=https://.*\.vercel\.app` para previews.
2. Vercel: importa la carpeta `frontend/` y define
   `VITE_API_BASE_URL=https://tu-servicio.onrender.com`.
3. En Vercel, variables de entorno: `VITE_API_BASE_URL`. No es necesario definir
   ninguna otra; el backend expone toda la API en `/api/*`.

Luego todas las llamadas del frontend van directamente al backend de Render
(y las firmas de factura apuntan a Supabase), sin pasar por Vercel, lo que
evita límites de tamaño de subida de facturas.

## Decisiones y límites conocidos

- **Un único servicio y una única base de datos.** Sin RabbitMQ ni outbox; las
  operaciones de venta y stock son transaccionales en la misma sesión.
- **Nunca commitees `.env`:** ya está ignorado por `.gitignore`.
- **Sin migraciones**: las tablas se crean con `create_all` al arrancar.
- **Sin autenticación**: añade auth/JWT y CORS restringido antes de exponer.
- **Facturas requieren Supabase Storage**; las imágenes admiten disco local.
- **Dry-run por defecto** en notificaciones: no se envían mensajes reales.

## Conectar Supabase

1. En **Settings → API** copia `Project URL`, `anon public` y `service_role`.
2. Copia los valores a `.env` (ignorado por git).
3. En **Storage** crea:
   - `product-images` → **público**.
   - `sales-invoices` → **privado**.
4. Para PostgreSQL, copia la contraseña de la base de datos a
   `SUPABASE_DB_PASSWORD`. El servicio usa el host
   `db.<ref>.supabase.co` y crea el esquema `themis`.

Sin `SUPABASE_URL`, las imágenes se guardan en disco y las facturas quedan
deshabilitadas (HTTP 503) hasta configurar Storage.
