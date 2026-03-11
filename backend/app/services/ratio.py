def calculate_ratio(caffeine_mg: int, price_cents: int) -> float:
    """mg of caffeine per unit of currency (e.g. per dollar or per real)."""
    if price_cents <= 0:
        raise ValueError("price_cents must be positive")
    return caffeine_mg / (price_cents / 100.0)
