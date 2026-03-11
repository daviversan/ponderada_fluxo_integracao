import uuid

from sqlalchemy import Column, Text, Integer, Float, CheckConstraint

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(Text, nullable=False)
    price_cents = Column(Integer, nullable=False)
    caffeine_mg = Column(Integer, nullable=False)
    caffeine_currency_ratio = Column(Float, nullable=False)
    currency = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("currency IN ('USD', 'BRL')", name="valid_currency"),
        CheckConstraint("price_cents > 0", name="positive_price"),
        CheckConstraint("caffeine_mg >= 0", name="non_negative_caffeine"),
    )
