"""Price-time priority limit order book implementation."""

# Future annotations avoid evaluation of type hints at import-time, keeping the module lightweight.
from __future__ import annotations

# bisect maintains a sorted list of price levels with logarithmic insert/find behaviour.
from bisect import bisect_left
# deque offers O(1) FIFO operations for orders queued at each price level.
from collections import deque
# Decimal mirrors the financial precision established on the Order entity.
from decimal import Decimal
# typing primitives document function contracts and aid static tooling.
from typing import Deque, Dict, Iterable, List, Optional

# Import domain objects and events so the book can both consume orders and emit outcomes.
from app.engine.events import OrderAccepted, OrderCancelled, OrderRejected, Trade
from app.engine.order import Order
from app.schema import Side, TimeInForce


class OrderBookSide:
    """Maintains the active orders for a single side (bid or ask) of the book."""

    def __init__(self, side: Side) -> None:
        # Store whether this side represents buy or sell orders for comparison logic.
        self.side = side
        # List of active prices kept sorted ascending for easy best-price calculation.
        self._prices: List[Decimal] = []
        # Map from price -> queue of FIFO orders at that level.
        self._levels: Dict[Decimal, Deque[Order]] = {}

    def add(self, order: Order) -> None:
        """Insert an order at the end of its price level queue."""

        level = self._levels.get(order.price)
        if level is None:
            # New price level; insert into sorted price list and prime an empty queue.
            index = bisect_left(self._prices, order.price)
            self._prices.insert(index, order.price)
            level = deque()
            self._levels[order.price] = level
        level.append(order)

    def best_price(self) -> Optional[Decimal]:
        """Return the top-of-book price for the side, if present."""

        if not self._prices:
            return None
        return self._prices[-1] if self.side is Side.BUY else self._prices[0]

    def best_order(self) -> Optional[Order]:
        """Return the next order eligible for matching while pruning empty queues."""

        price = self.best_price()
        if price is None:
            return None
        level = self._levels.get(price)
        if not level:
            # Remove stale level before trying again.
            self._remove_price(price)
            return self.best_order()
        # Ensure the head order still has quantity before returning it.
        while level and level[0].is_filled:
            level.popleft()
        if not level:
            self._remove_price(price)
            return self.best_order()
        return level[0]

    def remove_order(self, order: Order) -> None:
        """Strip an order from its level (used by cancel flows)."""

        level = self._levels.get(order.price)
        if not level:
            return
        try:
            level.remove(order)
        except ValueError:
            return
        if not level:
            self._remove_price(order.price)

    def _remove_price(self, price: Decimal) -> None:
        """Drop bookkeeping for a now-empty price level."""

        if price in self._levels:
            del self._levels[price]
        index = bisect_left(self._prices, price)
        if index < len(self._prices) and self._prices[index] == price:
            self._prices.pop(index)

    def all_orders(self) -> Iterable[Order]:
        """Iterate through orders in price-time priority (mainly for diagnostics)."""

        prices = reversed(self._prices) if self.side is Side.BUY else self._prices
        for price in prices:
            level = self._levels.get(price)
            if not level:
                continue
            for order in level:
                if not order.is_filled:
                    yield order


class OrderBook:
    """Coordinates bids and asks while producing domain events for external consumers."""

    def __init__(self) -> None:
        # Separate containers keep comparison logic trivial when matching cross-side.
        self._bids = OrderBookSide(Side.BUY)
        self._asks = OrderBookSide(Side.SELL)
        # Registry of active orders enables constant-time lookup on cancellation.
        self._orders: Dict[str, Order] = {}

    def submit(self, order: Order) -> List[object]:
        """Process an incoming order and return the emitted events."""

        events: List[object] = []
        opposite = self._asks if order.side is Side.BUY else self._bids
        same_side = self._bids if order.side is Side.BUY else self._asks

        # Run the core matching loop until either the order is filled or no contra side remains.
        while order.remaining_quantity > 0:
            best = opposite.best_order()
            if best is None:
                break
            if not self._crosses(order, best.price):
                break
            traded = min(order.remaining_quantity, best.remaining_quantity)
            best.apply_fill(traded)
            order.apply_fill(traded)
            events.append(Trade(
                maker_order_id=best.order_id,
                taker_order_id=order.order_id,
                price=best.price,
                quantity=traded,
            ))
            if best.is_filled:
                # Removing the filled order from the book keeps subsequent lookups clean.
                opposite.remove_order(best)
                self._drop_order(best)

        # Decide whether any remainder should rest on the book.
        if order.remaining_quantity > 0:
            if order.time_in_force is TimeInForce.IOC:
                events.append(OrderCancelled(
                    order_id=order.order_id,
                    remaining_quantity=order.remaining_quantity,
                    reason="IOC remainder",
                ))
            else:
                same_side.add(order)
                self._orders[order.order_id] = order
                events.append(OrderAccepted(order=order))
        else:
            # Fully filled IOC orders never joined the book but we still want to acknowledge them.
            events.append(OrderAccepted(order=order))
        return events

    def cancel(self, order_id: str, reason: str = "user_request") -> List[object]:
        """Attempt to cancel an order by ID, returning the resulting event."""

        order = self._orders.get(order_id)
        if not order:
            return [OrderRejected(order_id=order_id, reason="unknown_order")]
        side = self._bids if order.side is Side.BUY else self._asks
        side.remove_order(order)
        self._drop_order(order)
        return [OrderCancelled(order_id=order_id, remaining_quantity=order.remaining_quantity, reason=reason)]

    def best_bid(self) -> Optional[Decimal]:
        """Expose the highest bid for inspection/testing."""

        return self._bids.best_price()

    def best_ask(self) -> Optional[Decimal]:
        """Expose the lowest ask for inspection/testing."""

        return self._asks.best_price()

    def _drop_order(self, order: Order) -> None:
        """Remove an order from tracking once it is fully filled or cancelled."""

        if order.order_id in self._orders:
            del self._orders[order.order_id]

    def _crosses(self, incoming: Order, contra_price: Decimal) -> bool:
        """Check if an incoming order is marketable against the given contra price."""

        if incoming.side is Side.BUY:
            return incoming.price >= contra_price
        return incoming.price <= contra_price

    def snapshot(self) -> Dict[str, List[Order]]:
        """Return a shallow view of current resting orders, grouped by side for debugging."""

        return {
            "bids": list(self._bids.all_orders()),
            "asks": list(self._asks.all_orders()),
        }
