from app.cart import total_cents


def test_total_basic():
    assert total_cents([{"cents": 1000}, {"cents": 999}]) == 1999
