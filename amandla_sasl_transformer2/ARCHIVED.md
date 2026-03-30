# ARCHIVED — amandla_sasl_transformer2

> **Status:** Archived — do not use for new development.

## What is this?

This directory contains an **older, experimental version** of the SASL transformer
that was developed during an earlier sprint.

It is preserved here for reference only.

## Active Version

The **currently used** SASL transformer is located at:

```
sasl_transformer/           ← use this
  __init__.py
  config.py
  grammar_rules.py
  models.py
  routes.py
  sign_library.py
  transformer.py
  websocket_handler.py
```

It is imported by `backend/main.py`:

```python
from sasl_transformer.routes import router as sasl_router
app.include_router(sasl_router, prefix="/api/sasl")
```

## Why archived?

| Issue | Detail |
|-------|--------|
| Duplicate code | Exact same logic split across two directories — confusing |
| No active imports | `backend/main.py` imports from `sasl_transformer/`, not this directory |
| Outdated models | Uses older Pydantic v1 patterns; active version uses v2 |

## Safe to delete?

Yes — this entire `amandla_sasl_transformer2/` directory can be safely deleted
once you confirm the active `sasl_transformer/` is working correctly.

Run the SASL health check to verify:

```bash
curl http://localhost:8000/api/sasl/health
```

