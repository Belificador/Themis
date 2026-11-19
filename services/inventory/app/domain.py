from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

DEPLETED = "depleted"
NORMAL = "normal"


@dataclass(frozen=True)
class StockTransition:
    alert_state: str
    event_type: Optional[str]


def evaluate_transition(
    alert_state: str, new_quantity: int, threshold: int
) -> StockTransition:
    """Pure hysteresis rule for stock alerts.

    - normal -> low  : emit stock.depleted
    - depleted -> ok : emit stock.replenished
    - otherwise      : no event (avoids repeated alerts while in the same state)
    """
    is_low = new_quantity <= threshold

    if alert_state != DEPLETED and is_low:
        return StockTransition(DEPLETED, "stock.depleted")
    if alert_state == DEPLETED and not is_low:
        return StockTransition(NORMAL, "stock.replenished")
    return StockTransition(alert_state, None)
