---
name: dynamic-phone-inventory-microservices
description: Diseña e implementa microservicios desacoplados para catálogo dinámico de teléfonos, control de stock y eventos de sin stock. Usar al crear o modificar servicios de productos, inventario o mensajería de alertas.
---

# Dynamic Phone Inventory Microservices

## Principios obligatorios
1. **Catálogo 100% dinámico:** Jamás hardcodear marcas, modelos, capacidades o reglas fijas en código. Todo producto nuevo debe crearse vía API/UI con validaciones de esquema (SKU/identificador único, marca, modelo, variantes, umbral de stock).
2. **Desacoplamiento estricto:**
   - Cada microservicio posee su propio almacenamiento y modelo de datos.
   - Prohibido que un servicio consulte directamente la base de datos de otro.
   - La comunicación entre inventario y notificaciones debe pasar por eventos/colas o contratos explícitos.
3. **Eventos de stock agotado:**
   - Cuando el stock de un producto llegue a cero (o al umbral mínimo configurado), emitir un evento estructurado con: `event_id`, `event_type` (`stock.depleted`), `product_id`, `sku`, `product_name`, `current_stock`, `threshold` y `timestamp`.
4. **Calidad y trazabilidad:**
   - Validar entradas en los bordes de cada servicio.
   - Propagar un `correlation_id` o `event_id` para rastrear desde el cambio de stock hasta el envío de la alerta.
   - Documentar variables de entorno en `.env.example` y no dejar secretos en el código.
