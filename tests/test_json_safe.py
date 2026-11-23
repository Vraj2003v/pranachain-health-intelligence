"""A reply that holds NaN or infinity must still be written as JSON (the assistant answered 500 on one)."""
import json
import math

from api.main import _finite


def test_nan_and_infinity_become_none():
    out = _finite({"a": math.nan, "b": [1.5, math.inf, {"c": -math.inf}], "d": "text", "e": 3})
    assert out == {"a": None, "b": [1.5, None, {"c": None}], "d": "text", "e": 3}
    json.dumps(out, allow_nan=False)


def test_normal_values_are_unchanged():
    data = {"text": "ok", "n": 2.5, "trace": {"route": "model", "checks": [True, False]}}
    assert _finite(data) == data
