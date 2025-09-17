"""Service layer responsible for orchestrating the order book and event publishing."""

# typing.Callable lets us accept any callable event sink without imposing a concrete bus.
from typing import Callable, Iterable, Optional

# Import the order entity and book implementation that do the heavy lifting.
from app.engine.order import Order
from app.engine.orderbook import OrderBook


class MatchingEngine:
    """Thin façade that routes orders to the book and broadcasts resulting events."""

    def __init__(self, publish: Optional[Callable[[object], None]] = None) -> None:
        # Allow dependency-injected publisher; default to a no-op lambda for standalone usage.
        self._publish = publish or (lambda event: None)
        self._book = OrderBook()

    def submit_order(self, order: Order) -> Iterable[object]:
        """Send an order into the book and forward emitted events to the publisher."""

        events = self._book.submit(order)
        for event in events:
            self._publish(event)
        return events

    def cancel_order(self, order_id: str, reason: str = "user_request") -> Iterable[object]:
        """Request cancellation of an order and propagate resulting events."""

        events = self._book.cancel(order_id, reason=reason)
        for event in events:
            self._publish(event)
        return events

    def best_bid(self):
        """Proxy helper to inspect the book's best bid (useful in tests or monitoring)."""

        return self._book.best_bid()

    def best_ask(self):
        """Proxy helper mirroring :func:`best_bid` for the ask side."""

        return self._book.best_ask()

    @property
    def orderbook(self) -> OrderBook:
        """Expose the underlying order book for read-only inspection or advanced workflows."""

        return self._book
