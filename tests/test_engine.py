"""Integration tests for the higher-level matching engine façade."""

# collections.deque acts as a simple stand-in event bus sink we can inspect.
from collections import deque
# Decimal stays consistent with the pricing units used by the order book tests.
from decimal import Decimal

# Import the orchestrator and order entity under test.
from app.engine.matchine_engine import MatchingEngine
from app.engine.order import Order
# schema.Side enumerates the direction (buy/sell) needed for constructing orders.
from app.schema import Side


def make_order(order_id: str, side: Side, price: str, quantity: str) -> Order:
    """Factory mirroring the helper in order book tests for cross-module reuse."""

    return Order(
        order_id=order_id,
        side=side,
        price=Decimal(price),
        quantity=Decimal(quantity),
    )


def test_engine_publishes_events_to_sink():
    bus = deque()
    engine = MatchingEngine(publish=bus.append)

    engine.submit_order(make_order("ask-1", Side.SELL, "100", "1"))
    engine.submit_order(make_order("bid-1", Side.BUY, "101", "1"))

    assert len(bus) >= 3  # accept + trade + accept
    trade_events = [event for event in bus if event.__class__.__name__ == "Trade"]
    assert trade_events
    trade = trade_events[0]
    assert trade.maker_order_id == "ask-1"
    assert trade.taker_order_id == "bid-1"


def test_engine_cancel_produces_reject_for_unknown_id():
    bus = deque()
    engine = MatchingEngine(publish=bus.append)

    events = list(engine.cancel_order("missing"))

    assert events[0].reason == "unknown_order"
