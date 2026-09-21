from app.main import _probability


def test_noul_probability_is_returned():
    assert _probability({"noul": 0.74}) == 0.74


def test_invalid_noul_probability_is_rejected():
    try:
        _probability({"noul": 1.2})
    except ValueError:
        return
    raise AssertionError("invalid model output must not be accepted")
