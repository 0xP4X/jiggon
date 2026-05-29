from dataclasses import dataclass


@dataclass(frozen=True)
class SessionDecision:
    hour: int
    weekday: int
    winrate: float
    confidence_multiplier: int
    allow_trading: bool
    sample_size: int = 0


def approve_session(
    hour: int,
    weekday: int,
    winrate: float,
    minimum_winrate: float = 0.65,
    sample_size: int = 0,
    minimum_sample_size: int = 30,
) -> SessionDecision:
    if not 0 <= hour <= 23:
        raise ValueError("hour must be between 0 and 23")
    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be between 0 and 6")
    if not 0 <= winrate <= 1:
        raise ValueError("winrate must be between 0 and 1")

    allow_trading = winrate >= minimum_winrate and sample_size >= minimum_sample_size
    multiplier = 15 if winrate >= 0.73 else 0
    if winrate < minimum_winrate or sample_size < minimum_sample_size:
        multiplier = -20

    return SessionDecision(
        hour=hour,
        weekday=weekday,
        winrate=winrate,
        confidence_multiplier=multiplier,
        allow_trading=allow_trading,
        sample_size=sample_size,
    )
