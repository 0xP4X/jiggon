from app.strategy.confidence import ConfidenceInputs, approved, confidence_score


def test_confidence_score_matches_spec_weights():
    score = confidence_score(
        ConfidenceInputs(
            ema_aligned=True,
            rsi_confirmed=True,
            atr_valid=True,
            session_profitable=True,
            candle_strong=False,
            momentum_valid=True,
        )
    )

    assert score == 85
    assert approved(score)


def test_confidence_rejects_weak_setup():
    score = confidence_score(
        ConfidenceInputs(
            ema_aligned=True,
            rsi_confirmed=False,
            atr_valid=True,
            session_profitable=False,
            candle_strong=False,
            momentum_valid=True,
        )
    )

    assert score == 50
    assert not approved(score)
