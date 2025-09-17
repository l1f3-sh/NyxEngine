"""Domain events emitted by the order book during matching operations."""

# dataclass keeps event payloads lightweight, structured, and serializable.
from dataclasses import dataclass, field
from decimal import Decimal             # Decimal mirrors the precision of the order entities for price/size fields.
# datetime stamps events so downstream consumers can order them if needed.
from datetime import datetime, timezone
# typing aids readability for optional payloads (e.g., textual reason codes).
from typing import Optional

# Import the order type to embed copies of accepted orders in events.
from app.engine.order import Order


def _now() -> datetime:
    """Helper returning a timezone-aware timestamp for event emission."""

    return datetime.now(timezone.utc)


@dataclass(slots=True)
class OrderAccepted:
    """Published when a new order is accepted onto the book."""

    order: Order
    timestamp: datetime = field(default_factory=_now)


@dataclass(slots=True)
class Trade:
    """Represents an execution occurring between a resting and an aggressive order."""

    maker_order_id: str
    taker_order_id: str
    price: Decimal
    quantity: Decimal
    timestamp: datetime = field(default_factory=_now)


@dataclass(slots=True)
class OrderCancelled:
    """Signals that an order has been cancelled and removed from the book."""

    order_id: str
    remaining_quantity: Decimal
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=_now)


@dataclass(slots=True)
class OrderRejected:
    """Indicates the order could not be accepted for business reasons."""

    order_id: str
    reason: str
    timestamp: datetime = field(default_factory=_now)
