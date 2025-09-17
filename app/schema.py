"""Shared data structures and enumerations used across NyxEngine."""

# Enum gives us symbolic, readable constants for shared attributes like side/type.
from enum import Enum


class Side(str, Enum):
    """Identifies whether an order is attempting to buy or sell."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Represents the supported order entry styles."""

    LIMIT = "LIMIT"


class TimeInForce(str, Enum):
    """Controls how long an order should remain active on the book."""

    GTC = "GTC"  # Good-Till-Cancelled (default behaviour)
    IOC = "IOC"  # Immediate-Or-Cancel (fill remainder immediately or cancel)
