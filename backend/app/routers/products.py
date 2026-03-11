from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    CaffeineLookupResult,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app import crud
from app.services.external_api import lookup_caffeine

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, product_in)


@router.get("/search", response_model=List[ProductResponse])
def search_products(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return crud.search_products(db, q)


@router.get("/ranked", response_model=List[ProductResponse])
def ranked_products(db: Session = Depends(get_db)):
    return crud.get_ranked_products(db)


@router.get("/lookup", response_model=List[CaffeineLookupResult])
async def lookup_caffeine_info(q: str = Query(..., min_length=1)):
    return await lookup_caffeine(q)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return crud.list_products(db)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str, product_in: ProductUpdate, db: Session = Depends(get_db)
):
    product = crud.update_product(db, product_id, product_in)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: str, db: Session = Depends(get_db)):
    deleted = crud.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
