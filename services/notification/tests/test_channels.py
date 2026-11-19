import unittest

from app.channels import Alert, format_alert


class AlertFormattingTests(unittest.TestCase):
    def _alert(self, event_type: str) -> Alert:
        return Alert.from_payload(
            {
                "event_id": "evt-1",
                "event_type": event_type,
                "product_id": "prod-1",
                "sku": "IPH-15-128-BLK",
                "product_name": "Apple iPhone 15 128GB Negro",
                "current_stock": 0,
                "threshold": 1,
                "timestamp": "2026-11-19T10:00:00+00:00",
                "correlation_id": "cid-1",
            }
        )

    def test_depleted_message_is_actionable(self):
        text = format_alert(self._alert("stock.depleted"))
        self.assertIn("SIN STOCK", text)
        self.assertIn("IPH-15-128-BLK", text)
        self.assertIn("Stock actual: 0", text)
        self.assertIn("evt-1", text)

    def test_replenished_message(self):
        text = format_alert(self._alert("stock.replenished"))
        self.assertIn("STOCK RECUPERADO", text)

    def test_alert_from_payload_normalizes_state(self):
        alert = self._alert("stock.depleted")
        self.assertEqual(alert.stock_state, "depleted")
        self.assertEqual(alert.current_stock, 0)
        self.assertEqual(alert.correlation_id, "cid-1")


if __name__ == "__main__":
    unittest.main()
