# NyxEngine

```file
nyxengine/
  app/
    main.py               # FastAPI app + routes (TBD)
    schema.py             # Shared enums and types
    engine/
      order.py            # Order entity
      orderbook.py        # Order book, price levels, matching
      events.py           # Trade/Cancel/Reject events
      matchine_engine.py  # Matching engine (service orchestration)
    infra/
      bus.py              # Event bus (noop placeholder)
      storage.py          # Persistence adapter (noop placeholder)
      metrics.py          # (later) Prometheus/logging hooks
  tests/
    test_orderbook.py     # Order book behavior tests
    test_engine.py        # Engine orchestration tests (TBD)
    test_api.py           # API tests (TBD)
```

Getting started
- The core matching logic lives in `app/engine/orderbook.py` and is exercised by `tests/test_orderbook.py`.
- Order and enum definitions are in `app/engine/order.py` and `app/schema.py`.
- Infra stubs are placeholders to be implemented later.
