"""Order domain object capturing state required by the matching engine."""

# dataclass supplies concise syntax for domain entities with value semantics.
from dataclasses import dataclass, field
# Decimal keeps price/quantity arithmetic precise and avoids floating point drift.
from decimal import Decimal
# datetime stamps an order for time-priority decisions on the book.
from datetime import datetime, timezone
# typing annotations clarify optional/return types for readers and tools.
from typing import Optional

# Import shared enumerations so the engine agrees on canonical order metadata.
from app.schema import OrderType, Side, TimeInForce


# Shared zero literal avoids repeatedly constructing Decimal('0') instances.
DecimalZero = Decimal("0")


@dataclass(slots=True)
class Order:
    """Represents a single limit order resting on, or submitted to, the book."""

    order_id: str
    side: Side
    price: Decimal
    quantity: Decimal
    order_type: OrderType = OrderType.LIMIT
    time_in_force: TimeInForce = TimeInForce.GTC
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_quantity: Decimal = field(default=DecimalZero)
    user_data: Optional[dict] = None  # Preserve arbitrary metadata for higher layers.

    def __post_init__(self) -> None:
        """Validate numeric invariants immediately after construction."""

        if self.price <= DecimalZero:
            raise ValueError("price must be positive")
        if self.quantity <= DecimalZero:
            raise ValueError("quantity must be positive")
        if self.order_type is not OrderType.LIMIT:
            raise ValueError("Only LIMIT orders are supported by this engine version")

    @property
    def remaining_quantity(self) -> Decimal:
        """Return the unfilled portion that can still be matched."""

        remaining = self.quantity - self.filled_quantity
        return remaining if remaining > DecimalZero else DecimalZero

    @property
    def is_filled(self) -> bool:
        """Convenience flag signaling the order has reached zero remaining size."""

        return self.remaining_quantity == DecimalZero

    def apply_fill(self, filled: Decimal) -> Decimal:
        """Reduce remaining quantity by `filled` and return the actual amount applied."""

        if filled <= DecimalZero:
            raise ValueError("filled must be positive")
        actual_fill = min(filled, self.remaining_quantity)
        self.filled_quantity += actual_fill
        return actual_fill

    def clone_for_remainder(self) -> "Order":
        """Produce a shallow copy capturing leftover state (useful for IOC rejection)."""

        remainder = self.remaining_quantity
        if remainder <= DecimalZero:
            raise ValueError('order is fully filled; nothing to clone')
        return Order(
            order_id=self.order_id,
            side=self.side,
            price=self.price,
            quantity=remainder,
            order_type=self.order_type,
            time_in_force=self.time_in_force,
            created_at=self.created_at,
            filled_quantity=DecimalZero,
            user_data=self.user_data.copy() if isinstance(self.user_data, dict) else self.user_data,
        )
