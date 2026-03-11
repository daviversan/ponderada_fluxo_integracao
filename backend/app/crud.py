import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Product
from app.schemas import ProductCreate, ProductUpdate
from app.services.ratio import calculate_ratio


def create_product(db: Session, product_in: ProductCreate) -> Product:
    ratio = calculate_ratio(product_in.caffeine_mg, product_in.price_cents)
    product = Product(
        id=str(uuid.uuid4()),
        name=product_in.name,
        price_cents=product_in.price_cents,
        caffeine_mg=product_in.caffeine_mg,
        caffeine_currency_ratio=ratio,
        currency=product_in.currency.value,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: str) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def list_products(db: Session) -> List[Product]:
    return db.query(Product).all()


def update_product(
    db: Session, product_id: str, product_in: ProductUpdate
) -> Optional[Product]:
    product = get_product(db, product_id)
    if product is None:
        return None

    update_data = product_in.model_dump(exclude_unset=True)
    if "currency" in update_data and update_data["currency"] is not None:
        update_data["currency"] = update_data["currency"].value

    for field, value in update_data.items():
        setattr(product, field, value)

    price = update_data.get("price_cents", product.price_cents)
    caffeine = update_data.get("caffeine_mg", product.caffeine_mg)
    product.caffeine_currency_ratio = calculate_ratio(caffeine, price)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: str) -> bool:
    product = get_product(db, product_id)
    if product is None:
        return False
    db.delete(product)
    db.commit()
    return True


def search_products(db: Session, query: str) -> List[Product]:
    return (
        db.query(Product).filter(Product.name.ilike(f"%{query}%")).all()
    )


def get_ranked_products(db: Session) -> List[Product]:
    return (
        db.query(Product)
        .order_by(Product.caffeine_currency_ratio.desc())
        .all()
    )
