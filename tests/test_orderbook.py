"""Unit tests covering the core order book matching behaviour."""

# Decimal keeps assertions deterministic for price/size comparisons.
from decimal import Decimal

# Import the subject under test and its supporting domain types.
from app.engine.order import Order
from app.engine.orderbook import OrderBook
from app.schema import Side, TimeInForce


def make_order(**overrides):
    """Helper that constructs an order with reasonable defaults for tests."""

    base = dict(
        order_id=overrides.get("order_id", "order-1"),
        side=overrides.get("side", Side.BUY),
        price=overrides.get("price", Decimal("100")),
        quantity=overrides.get("quantity", Decimal("1")),
        time_in_force=overrides.get("time_in_force", TimeInForce.GTC),
    )
    return Order(**base)


def test_limit_order_rests_when_no_contra_side():
    book = OrderBook()

    events = book.submit(make_order(order_id="bid-1"))

    assert len(events) == 1
    assert book.best_bid() == Decimal("100")
    assert book.best_ask() is None


def test_crossing_order_executes_and_clears_book():
    book = OrderBook()

    book.submit(make_order(order_id="ask-1", side=Side.SELL))
    events = book.submit(make_order(order_id="bid-1", side=Side.BUY, price=Decimal("101")))

    trade_events = [event for event in events if event.__class__.__name__ == "Trade"]
    assert len(trade_events) == 1
    trade = trade_events[0]
    assert trade.maker_order_id == "ask-1"
    assert trade.taker_order_id == "bid-1"
    assert trade.price == Decimal("100")
    assert trade.quantity == Decimal("1")
    assert book.best_bid() is None
    assert book.best_ask() is None


def test_partial_fill_leaves_remainder_on_book():
    book = OrderBook()

    resting = make_order(order_id="ask-1", side=Side.SELL, quantity=Decimal("5"))
    book.submit(resting)

    events = book.submit(make_order(order_id="bid-1", side=Side.BUY, price=Decimal("100"), quantity=Decimal("2")))

    trade_events = [event for event in events if event.__class__.__name__ == "Trade"]
    assert trade_events[0].quantity == Decimal("2")
    assert resting.remaining_quantity == Decimal("3")
    assert book.best_ask() == Decimal("100")


def test_ioc_cancels_unfilled_remainder():
    book = OrderBook()

    book.submit(make_order(order_id="ask-1", side=Side.SELL, quantity=Decimal("1")))

    events = book.submit(make_order(
        order_id="bid-1",
        side=Side.BUY,
        price=Decimal("120"),
        quantity=Decimal("2"),
        time_in_force=TimeInForce.IOC,
    ))

    trade_events = [event for event in events if event.__class__.__name__ == "Trade"]
    cancel_events = [event for event in events if event.__class__.__name__ == "OrderCancelled"]
    assert trade_events[0].quantity == Decimal("1")
    assert cancel_events[0].remaining_quantity == Decimal("1")
    assert book.best_bid() is None
    assert book.best_ask() is None


def test_cancelling_unknown_order_is_rejected():
    book = OrderBook()

    events = book.cancel("does-not-exist")

    reject = events[0]
    assert reject.reason == "unknown_order"
