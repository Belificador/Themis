from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from app.alerts import _state_for
from app.schemas import ProductBase, SaleCreate, SaleItemCreate
from app.service import _sale_number


class AlertStateTests(unittest.TestCase):
    def test_depleted_at_zero(self) -> None:
        self.assertEqual(_state_for(0, 0), "depleted")
        self.assertEqual(_state_for(0, 5), "depleted")

    def test_low_at_or_below_threshold(self) -> None:
        self.assertEqual(_state_for(1, 1), "low")
        self.assertEqual(_state_for(2, 5), "low")

    def test_normal_above_threshold(self) -> None:
        self.assertEqual(_state_for(3, 1), "normal")
        self.assertEqual(_state_for(1, 0), "normal")


class SaleNumberTests(unittest.TestCase):
    def test_format(self) -> None:
        sale_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        created = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(_sale_number(sale_id, created), "V-20261123-123456")


class SaleSchemaTests(unittest.TestCase):
    def _base_payload(self):
        return SaleCreate(
            items=[
                SaleItemCreate(
                    product_id=uuid.uuid4(),
                    quantity=1,
                    imei="IMEI123456789",
                )
            ],
            customer_name="Cliente Test",
            vendedor="Vendedor Test",
        )

    def test_vendedor_is_stripped(self) -> None:
        payload = self._base_payload()
        payload.vendedor = "  Ana Pérez  "
        # Re-validar pasando de nuevo por el constructor con valor limpio
        payload = SaleCreate(
            items=[
                SaleItemCreate(
                    product_id=uuid.uuid4(),
                    quantity=1,
                    imei="IMEI123456789",
                )
            ],
            customer_name="Cliente Test",
            vendedor="  Ana Pérez  ",
        )
        self.assertEqual(payload.vendedor, "Ana Pérez")

    def test_blank_vendedor_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SaleCreate(
                items=[
                    SaleItemCreate(
                        product_id=uuid.uuid4(),
                        quantity=1,
                        imei="IMEI123456789",
                    )
                ],
                customer_name="Cliente Test",
                vendedor="   ",
            )

    def test_blank_customer_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SaleCreate(
                items=[
                    SaleItemCreate(
                        product_id=uuid.uuid4(),
                        quantity=1,
                        imei="IMEI123456789",
                    )
                ],
                customer_name="   ",
                vendedor="Vendedor Test",
            )

    def test_imei_is_optional(self) -> None:
        payload = SaleCreate(
            items=[
                SaleItemCreate(
                    product_id=uuid.uuid4(),
                    quantity=1,
                    imei="",
                )
            ],
            customer_name="Cliente Test",
            vendedor="Vendedor Test",
        )
        self.assertEqual(len(payload.items), 1)
        self.assertEqual(payload.items[0].imeis, [])

    def test_multiple_imeis_are_cleaned(self) -> None:
        payload = SaleItemCreate(
            product_id=uuid.uuid4(),
            quantity=2,
            imeis=[" 351234567890123 ", "", "351234567890124"],
        )
        self.assertEqual(
            payload.imeis, ["351234567890123", "351234567890124"]
        )

    def test_cashea_payment_is_valid(self) -> None:
        payload = SaleCreate(
            items=[
                SaleItemCreate(
                    product_id=uuid.uuid4(),
                    quantity=1,
                    imei="IMEI123456789",
                )
            ],
            customer_name="Cliente Test",
            vendedor="Vendedor Test",
            payment_method="cashea",
        )
        self.assertEqual(payload.payment_method, "cashea")

    def test_unknown_payment_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SaleCreate(
                items=[
                    SaleItemCreate(
                        product_id=uuid.uuid4(),
                        quantity=1,
                        imei="IMEI123456789",
                    )
                ],
                customer_name="Cliente Test",
                vendedor="Vendedor Test",
                payment_method="bitcoin",
            )

    def test_default_currency_is_usd(self) -> None:
        payload = self._base_payload()
        self.assertEqual(payload.currency, "USD")

    def test_eur_currency_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SaleCreate(
                items=[
                    SaleItemCreate(
                        product_id=uuid.uuid4(),
                        quantity=1,
                        imei="IMEI123456789",
                    )
                ],
                customer_name="Cliente Test",
                vendedor="Vendedor Test",
                currency="EUR",
            )


class ProductSchemaTests(unittest.TestCase):
    def test_prices_required(self) -> None:
        with self.assertRaises(ValidationError):
            ProductBase(
                sku="SKU-1",
                brand="Tecno",
                model="Spark",
                color="Negro",
            )

    def test_text_fields_are_stripped(self) -> None:
        product = ProductBase(
            sku="  SKU-1  ",
            brand=" Tecno ",
            model=" Spark ",
            color=" Negro ",
            price_usd=110,
        )
        self.assertEqual(product.sku, "SKU-1")
        self.assertEqual(product.brand, "Tecno")


if __name__ == "__main__":
    unittest.main()
