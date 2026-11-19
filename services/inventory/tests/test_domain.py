import unittest

from app.domain import evaluate_transition


class TransitionTests(unittest.TestCase):
    def test_crossing_below_threshold_emits_depleted(self):
        result = evaluate_transition("normal", 0, 1)
        self.assertEqual(result.event_type, "stock.depleted")
        self.assertEqual(result.alert_state, "depleted")

    def test_reaching_threshold_emits_depleted(self):
        result = evaluate_transition("normal", 2, 2)
        self.assertEqual(result.event_type, "stock.depleted")

    def test_staying_low_does_not_emit(self):
        result = evaluate_transition("depleted", 0, 1)
        self.assertIsNone(result.event_type)
        self.assertEqual(result.alert_state, "depleted")

    def test_recovering_emits_replenished(self):
        result = evaluate_transition("depleted", 5, 1)
        self.assertEqual(result.event_type, "stock.replenished")
        self.assertEqual(result.alert_state, "normal")

    def test_normal_state_does_not_emit(self):
        result = evaluate_transition("normal", 5, 1)
        self.assertIsNone(result.event_type)
        self.assertEqual(result.alert_state, "normal")

    def test_threshold_zero_emits_at_zero(self):
        result = evaluate_transition("normal", 0, 0)
        self.assertEqual(result.event_type, "stock.depleted")


if __name__ == "__main__":
    unittest.main()
