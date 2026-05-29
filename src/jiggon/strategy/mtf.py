from dataclasses import dataclass

from jiggon.analysis.market import MarketSnapshot


@dataclass(frozen=True)
class MultiTimeframeContext:
    snapshot_1h: MarketSnapshot
    snapshot_4h: MarketSnapshot


def verify_mtf_alignment(direction: str, context: MultiTimeframeContext | None) -> bool:
    if not context:
        return True  # If no MTF provided, default to passing
    
    # Require the 1h trend to align with the trade direction
    if direction == "CALL":
        return context.snapshot_1h.trend in ("bullish", "mixed")
    elif direction == "PUT":
        return context.snapshot_1h.trend in ("bearish", "mixed")
    return False
