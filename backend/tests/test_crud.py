import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Product
from app.schemas import ProductCreate, ProductUpdate, Currency
from app import crud


def _make_product(**overrides) -> ProductCreate:
    defaults = {
        "name": "Test Coffee",
        "price_cents": 500,
        "caffeine_mg": 100,
        "currency": Currency.USD,
    }
    defaults.update(overrides)
    return ProductCreate(**defaults)


class TestCreateProduct:
    def test_creates_and_returns_product(self, db_session):
        product = crud.create_product(db_session, _make_product())

        assert product.id is not None
        assert product.name == "Test Coffee"
        assert product.price_cents == 500
        assert product.caffeine_mg == 100
        assert product.currency == "USD"

    def test_computes_ratio_on_create(self, db_session):
        product = crud.create_product(
            db_session, _make_product(caffeine_mg=200, price_cents=400)
        )
        # 200 / (400 / 100) = 50.0
        assert product.caffeine_currency_ratio == pytest.approx(50.0)

    def test_persists_to_database(self, db_session):
        product = crud.create_product(db_session, _make_product())

        found = db_session.query(Product).filter(Product.id == product.id).first()
        assert found is not None
        assert found.name == "Test Coffee"


class TestGetProduct:
    def test_returns_existing_product(self, db_session):
        created = crud.create_product(db_session, _make_product(name="Espresso"))

        fetched = crud.get_product(db_session, created.id)
        assert fetched is not None
        assert fetched.name == "Espresso"

    def test_returns_none_for_missing_id(self, db_session):
        assert crud.get_product(db_session, "nonexistent-id") is None


class TestListProducts:
    def test_returns_empty_list_initially(self, db_session):
        assert crud.list_products(db_session) == []

    def test_returns_all_products(self, db_session):
        crud.create_product(db_session, _make_product(name="Product A"))
        crud.create_product(db_session, _make_product(name="Product B"))
        crud.create_product(db_session, _make_product(name="Product C"))

        products = crud.list_products(db_session)
        assert len(products) == 3
        names = {p.name for p in products}
        assert names == {"Product A", "Product B", "Product C"}


class TestUpdateProduct:
    def test_updates_name(self, db_session):
        created = crud.create_product(db_session, _make_product(name="Old Name"))

        updated = crud.update_product(
            db_session, created.id, ProductUpdate(name="New Name")
        )
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.price_cents == 500  # unchanged

    def test_updates_price_and_recalculates_ratio(self, db_session):
        created = crud.create_product(
            db_session, _make_product(caffeine_mg=100, price_cents=500)
        )
        # original ratio: 100 / 5.0 = 20.0
        assert created.caffeine_currency_ratio == pytest.approx(20.0)

        updated = crud.update_product(
            db_session, created.id, ProductUpdate(price_cents=1000)
        )
        # new ratio: 100 / 10.0 = 10.0
        assert updated.caffeine_currency_ratio == pytest.approx(10.0)

    def test_updates_caffeine_and_recalculates_ratio(self, db_session):
        created = crud.create_product(
            db_session, _make_product(caffeine_mg=100, price_cents=500)
        )

        updated = crud.update_product(
            db_session, created.id, ProductUpdate(caffeine_mg=300)
        )
        # new ratio: 300 / 5.0 = 60.0
        assert updated.caffeine_currency_ratio == pytest.approx(60.0)

    def test_updates_currency(self, db_session):
        created = crud.create_product(
            db_session, _make_product(currency=Currency.USD)
        )

        updated = crud.update_product(
            db_session, created.id, ProductUpdate(currency=Currency.BRL)
        )
        assert updated.currency == "BRL"

    def test_returns_none_for_missing_id(self, db_session):
        result = crud.update_product(
            db_session, "nonexistent-id", ProductUpdate(name="X")
        )
        assert result is None


class TestDeleteProduct:
    def test_deletes_existing_product(self, db_session):
        created = crud.create_product(db_session, _make_product())

        assert crud.delete_product(db_session, created.id) is True
        assert crud.get_product(db_session, created.id) is None

    def test_returns_false_for_missing_id(self, db_session):
        assert crud.delete_product(db_session, "nonexistent-id") is False


class TestSearchProducts:
    def test_finds_matching_products(self, db_session):
        crud.create_product(db_session, _make_product(name="Red Bull"))
        crud.create_product(db_session, _make_product(name="Monster Energy"))
        crud.create_product(db_session, _make_product(name="Red Eye Coffee"))

        results = crud.search_products(db_session, "red")
        assert len(results) == 2
        names = {p.name for p in results}
        assert names == {"Red Bull", "Red Eye Coffee"}

    def test_returns_empty_for_no_match(self, db_session):
        crud.create_product(db_session, _make_product(name="Espresso"))

        results = crud.search_products(db_session, "matcha")
        assert results == []

    def test_case_insensitive_search(self, db_session):
        crud.create_product(db_session, _make_product(name="Starbucks Latte"))

        results = crud.search_products(db_session, "STARBUCKS")
        assert len(results) == 1
        assert results[0].name == "Starbucks Latte"


class TestGetRankedProducts:
    def test_returns_products_sorted_by_ratio_desc(self, db_session):
        # ratio = caffeine_mg / (price_cents / 100)
        crud.create_product(
            db_session, _make_product(name="Low Ratio", caffeine_mg=10, price_cents=1000)
        )  # ratio = 1.0
        crud.create_product(
            db_session, _make_product(name="High Ratio", caffeine_mg=300, price_cents=100)
        )  # ratio = 300.0
        crud.create_product(
            db_session, _make_product(name="Mid Ratio", caffeine_mg=100, price_cents=200)
        )  # ratio = 50.0

        ranked = crud.get_ranked_products(db_session)
        assert len(ranked) == 3
        assert ranked[0].name == "High Ratio"
        assert ranked[1].name == "Mid Ratio"
        assert ranked[2].name == "Low Ratio"

    def test_returns_empty_when_no_products(self, db_session):
        assert crud.get_ranked_products(db_session) == []


class TestDatabaseIntegrity:
    def test_rejects_invalid_currency_at_db_level(self, db_session):
        """DB CHECK constraint rejects currencies other than USD/BRL."""
        product = Product(
            id="test-id",
            name="Bad Currency",
            price_cents=100,
            caffeine_mg=50,
            caffeine_currency_ratio=50.0,
            currency="EUR",
        )
        db_session.add(product)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_rejects_zero_price_at_db_level(self, db_session):
        """DB CHECK constraint rejects price_cents <= 0."""
        product = Product(
            id="test-id",
            name="Zero Price",
            price_cents=0,
            caffeine_mg=50,
            caffeine_currency_ratio=0.0,
            currency="USD",
        )
        db_session.add(product)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_rejects_negative_caffeine_at_db_level(self, db_session):
        """DB CHECK constraint rejects caffeine_mg < 0."""
        product = Product(
            id="test-id",
            name="Negative Caffeine",
            price_cents=100,
            caffeine_mg=-10,
            caffeine_currency_ratio=0.0,
            currency="USD",
        )
        db_session.add(product)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_rollback_preserves_prior_data(self, db_session):
        """After a failed insert, previously committed data remains intact."""
        crud.create_product(db_session, _make_product(name="Good Product"))

        bad = Product(
            id="bad-id",
            name="Bad",
            price_cents=0,
            caffeine_mg=50,
            caffeine_currency_ratio=0.0,
            currency="USD",
        )
        db_session.add(bad)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

        products = crud.list_products(db_session)
        assert len(products) == 1
        assert products[0].name == "Good Product"

    def test_rejects_null_name(self, db_session):
        """NOT NULL constraint on name."""
        product = Product(
            id="test-id",
            name=None,
            price_cents=100,
            caffeine_mg=50,
            caffeine_currency_ratio=50.0,
            currency="USD",
        )
        db_session.add(product)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
