from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import schemas, crud, auth

router = APIRouter()

@router.get("/", response_model=schemas.CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    current_user = Depends(auth.get_current_active_user)
):
    items = crud.get_cart_items(db, current_user.id)
    
    # Calculate total
    total = 0
    for item in items:
        total += item.product.price * item.quantity
    
    return schemas.CartResponse(items=items, total=total)

@router.post("/add", response_model=schemas.CartItemResponse)
def add_to_cart(
    item: schemas.CartItemCreate,
    db: Session = Depends(get_db),
    current_user = Depends(auth.get_current_active_user)
):
    # Check product exists and has stock
    product = crud.get_product(db, item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.stock_quantity < item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    return crud.add_to_cart(db, current_user.id, item)

@router.delete("/{cart_item_id}")
def remove_from_cart(
    cart_item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(auth.get_current_active_user)
):
    crud.remove_from_cart(db, cart_item_id, current_user.id)
    return {"message": "Item removed from cart"}

@router.delete("/")
def clear_cart(
    db: Session = Depends(get_db),
    current_user = Depends(auth.get_current_active_user)
):
    crud.clear_cart(db, current_user.id)
    return {"message": "Cart cleared"}