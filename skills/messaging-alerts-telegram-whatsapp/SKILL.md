---
name: messaging-alerts-telegram-whatsapp
description: Implementa el microservicio o módulo de notificaciones a Telegram y WhatsApp ante eventos de falta de stock, con idempotencia, reintentos y formato claro. Usar al integrar bots o APIs de mensajería.
---

# Messaging Alerts (Telegram & WhatsApp)

## Principios obligatorios
1. **Aislamiento del canal:** La lógica de formato y envío a Telegram o WhatsApp debe vivir aislada del dominio de inventario. Si cambia el proveedor de WhatsApp o Telegram, no debe impactar el cálculo de stock.
2. **Idempotencia y anti-spam:**
   - Deduplicar alertas por `event_id` o por `(product_id, stock_state)` dentro de una ventana de tiempo para evitar enviar mensajes repetidos ante reintentos de red.
3. **Mensajes accionables:**
   - Cada alerta debe indicar claramente: producto/modelo, SKU/variante, stock actual (`0`), hora del evento y canal de destino.
4. **Resiliencia:**
   - Manejar timeouts, rate limits y fallos de red con reintentos controlados y registro de errores sin bloquear otros eventos.
