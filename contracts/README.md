# Contratos de eventos (v1)

Los contratos son la unica interfaz compartida entre servicios. Ningun servicio
lee la base de datos de otro: los cambios viajan como eventos persistentes por
RabbitMQ (exchange de tipo `topic`).

| Evento | Exchange | Routing key | Emisor | Consumidor |
| --- | --- | --- | --- | --- |
| `product.created` | `products` | `product.created` | catalog-service | inventory-service |
| `product.updated` | `products` | `product.updated` | catalog-service | inventory-service |
| `product.deleted` | `products` | `product.deleted` | catalog-service | inventory-service |
| `stock.depleted` | `stock` | `stock.depleted` | inventory-service | notification-service |
| `stock.replenished` | `stock` | `stock.replenished` | inventory-service | notification-service |

## Garantias

- **Entrega al menos una vez** mediante el patron *transactional outbox*.
- **Idempotencia** en consumidores: `notification-service` deduplica por
  `event_id` y por `(product_id, stock_state)` dentro de una ventana temporal.
- **Trazabilidad**: `correlation_id` viaja desde el request HTTP hasta el log de
  notificacion. Si no existe, cada servicio genera uno.
- **Versionado**: los esquemas viven en `contracts/*.schema.json`; cualquier
  cambio incompatible requiere una nueva version.

## Flujo

```
Cliente -> gateway -> catalog-service --product.*--> inventory-service
                                                        |
                                                        +--stock.*--> notification-service --> Telegram / WhatsApp
```
