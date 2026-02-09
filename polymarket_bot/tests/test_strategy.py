from strategy import BestQuote, OrderBookTop, decide, Mode


def test_negative_risk_arb_triggers():
    top = OrderBookTop(
        yes=BestQuote(bid=0.48, ask=0.48),
        no=BestQuote(bid=0.48, ask=0.48),
    )
    rec = decide(top, taker_fee=0.01, maker_edge=0.02, size=10)
    assert rec.mode == Mode.TAKER_ARB


def test_maker_when_no_arb():
    top = OrderBookTop(
        yes=BestQuote(bid=0.48, ask=0.52),
        no=BestQuote(bid=0.48, ask=0.52),
    )
    rec = decide(top, taker_fee=0.01, maker_edge=0.02, size=10)
    assert rec.mode == Mode.MAKER
    assert rec.price_yes is not None and 0 < rec.price_yes < 1
    assert rec.price_no is not None and 0 < rec.price_no < 1
