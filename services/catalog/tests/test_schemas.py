import unittest

from pydantic import ValidationError

from app.schemas import ProductCreate, ProductUpdate

VALID = {
    "sku": "IPH-15-128-BLK",
    "brand": "Apple",
    "model": "iPhone 15",
    "storage_gb": 128,
    "color": "Negro",
    "category": "phone",
    "cost_price_eur": 720.0,
    "price_eur": 999.0,
    "cost_price_usd": 780.0,
    "price_usd": 1080.0,
    "threshold": 1,
}


class ProductSchemaTests(unittest.TestCase):
    def test_valid_payload_keeps_dual_prices(self):
        product = ProductCreate(**VALID)
        self.assertEqual(product.price_eur, 999.0)
        self.assertEqual(product.price_usd, 1080.0)

    def test_blank_sku_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(**{**VALID, "sku": "   "})

    def test_negative_threshold_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(**{**VALID, "threshold": -1})

    def test_storage_zero_is_allowed_for_accessories(self):
        product = ProductCreate(**{**VALID, "storage_gb": 0})
        self.assertEqual(product.storage_gb, 0)

    def test_invalid_storage_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(**{**VALID, "storage_gb": 5000})

    def test_ram_is_optional(self):
        product = ProductCreate(**{**VALID, "ram_gb": 8})
        self.assertEqual(product.ram_gb, 8)

    def test_category_defaults_to_phone(self):
        payload = {key: value for key, value in VALID.items() if key != "category"}
        product = ProductCreate(**payload)
        self.assertEqual(product.category, "phone")

    def test_invalid_category_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(**{**VALID, "category": "laptop"})

    def test_negative_cost_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(**{**VALID, "cost_price_eur": -1})

    def test_negative_usd_cost_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(**{**VALID, "cost_price_usd": -1})

    def test_accessory_can_have_zero_cost(self):
        product = ProductCreate(
            **{
                **VALID,
                "category": "accessory",
                "cost_price_eur": 0,
                "cost_price_usd": 0,
            }
        )
        self.assertEqual(product.cost_price_eur, 0)
        self.assertEqual(product.cost_price_usd, 0)

    def test_partial_update_can_change_prices_and_category(self):
        update = ProductUpdate(
            threshold=3,
            cost_price_eur=699.0,
            price_eur=899.0,
            cost_price_usd=755.0,
            price_usd=971.0,
            category="tablet",
        )
        self.assertEqual(
            update.model_dump(exclude_unset=True),
            {
                "threshold": 3,
                "cost_price_eur": 699.0,
                "price_eur": 899.0,
                "cost_price_usd": 755.0,
                "price_usd": 971.0,
                "category": "tablet",
            },
        )


if __name__ == "__main__":
    unittest.main()
