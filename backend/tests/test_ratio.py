import pytest

from app.services.ratio import calculate_ratio


class TestCalculateRatio:
    def test_basic_ratio(self):
        # 100 mg caffeine, 500 cents ($5.00) -> 100 / 5.0 = 20.0
        assert calculate_ratio(100, 500) == pytest.approx(20.0)

    def test_high_caffeine_low_price(self):
        # 200 mg caffeine, 100 cents ($1.00) -> 200 / 1.0 = 200.0
        assert calculate_ratio(200, 100) == pytest.approx(200.0)

    def test_low_caffeine_high_price(self):
        # 50 mg caffeine, 1000 cents ($10.00) -> 50 / 10.0 = 5.0
        assert calculate_ratio(50, 1000) == pytest.approx(5.0)

    def test_one_cent_price(self):
        # 80 mg caffeine, 1 cent ($0.01) -> 80 / 0.01 = 8000.0
        assert calculate_ratio(80, 1) == pytest.approx(8000.0)

    def test_zero_caffeine(self):
        # 0 mg caffeine -> ratio is 0.0 regardless of price
        assert calculate_ratio(0, 250) == pytest.approx(0.0)

    def test_zero_price_raises(self):
        with pytest.raises(ValueError, match="price_cents must be positive"):
            calculate_ratio(100, 0)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="price_cents must be positive"):
            calculate_ratio(100, -50)

    def test_fractional_result(self):
        # 10 mg caffeine, 300 cents ($3.00) -> 10 / 3.0 ≈ 3.333...
        assert calculate_ratio(10, 300) == pytest.approx(10 / 3.0)

    def test_large_values(self):
        # 5000 mg caffeine, 99999 cents ($999.99) -> 5000 / 999.99
        expected = 5000 / (99999 / 100.0)
        assert calculate_ratio(5000, 99999) == pytest.approx(expected)
