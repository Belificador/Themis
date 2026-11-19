import unittest
import uuid

from pydantic import ValidationError

from app.schemas import SaleCreate


def payload(**overrides):
    data = {
        "items": [
            {
                "product_id": str(uuid.uuid4()),
                "quantity": 2,
                "unit_price": 129.99,
            }
        ],
        "payment_method": "card",
        "customer_name": "Ana",
        "idempotency_key": "sale-key-1",
    }
    data.update(overrides)
    return data


class SaleSchemaTests(unittest.TestCase):
    def test_valid_sale_defaults_and_prices(self):
        sale = SaleCreate(**payload())
        self.assertEqual(sale.payment_method, "card")
        self.assertEqual(sale.items[0].quantity, 2)
        self.assertEqual(sale.items[0].unit_price, 129.99)

    def test_payment_defaults_to_cash(self):
        data = payload()
        data.pop("payment_method")
        self.assertEqual(SaleCreate(**data).payment_method, "cash")

    def test_currency_defaults_to_eur(self):
        self.assertEqual(SaleCreate(**payload()).currency, "EUR")

    def test_currency_accepts_usd(self):
        self.assertEqual(SaleCreate(**payload(currency="USD")).currency, "USD")

    def test_invalid_currency_is_rejected(self):
        with self.assertRaises(ValidationError):
            SaleCreate(**payload(currency="GBP"))

    def test_empty_sale_is_rejected(self):
        with self.assertRaises(ValidationError):
            SaleCreate(**payload(items=[]))

    def test_zero_quantity_is_rejected(self):
        data = payload()
        data["items"][0]["quantity"] = 0
        with self.assertRaises(ValidationError):
            SaleCreate(**data)

    def test_negative_unit_price_is_rejected(self):
        data = payload()
        data["items"][0]["unit_price"] = -1
        with self.assertRaises(ValidationError):
            SaleCreate(**data)

    def test_blank_optional_text_becomes_none(self):
        sale = SaleCreate(**payload(customer_name="   ", note="  "))
        self.assertIsNone(sale.customer_name)
        self.assertIsNone(sale.note)


if __name__ == "__main__":
    unittest.main()
