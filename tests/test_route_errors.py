"""
Tests that HTTP routes never leak raw exception internals to clients
(D10 in MASTER_PLAN.md; closes the last defect from the research register).

Run with: pytest tests/test_route_errors.py -v
"""

import asyncio

import pytest
from fastapi import HTTPException

from sasl_transformer import routes
from sasl_transformer.models import TranslationRequest

SECRET_INTERNALS = "SECRET_INTERNAL_PATH_C__users_admin_token=abc123"


class ExplodingTransformer:
    def __init__(self, exc):
        self._exc = exc

    async def translate(self, request):
        raise self._exc


@pytest.fixture(autouse=True)
def _restore_singleton():
    original = routes._transformer
    yield
    routes._transformer = original


def _call_translate():
    request = TranslationRequest(english_text="hello")
    return asyncio.run(routes.translate_to_sasl(request))


def test_value_error_detail_is_generic():
    routes._transformer = ExplodingTransformer(ValueError(SECRET_INTERNALS))
    with pytest.raises(HTTPException) as exc_info:
        _call_translate()
    assert exc_info.value.status_code == 400
    assert SECRET_INTERNALS not in str(exc_info.value.detail)


def test_unexpected_error_detail_is_generic():
    routes._transformer = ExplodingTransformer(RuntimeError(SECRET_INTERNALS))
    with pytest.raises(HTTPException) as exc_info:
        _call_translate()
    assert exc_info.value.status_code == 500
    assert SECRET_INTERNALS not in str(exc_info.value.detail)
