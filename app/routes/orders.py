from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import schemas, crud, auth

router = APIRouter()

@router.post("/create", response_model=schemas.OrderResponse)
def create_order(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(auth.get_current_active_user)
):
    # Validate all products exist and have enough stock
    for item in order_data.items:
        product = crud.get_product(db, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        if product.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
    
    order = crud.create_order(db, current_user.id, order_data)
    
    # Convert order items to dict for response
    order_items = []
    for item in order.order_items:
        order_items.append({
            "product_name": item.product.name,
            "quantity": item.quantity,
            "size": item.size,
            "color": item.color,
            "price": item.price_at_time
        })
    
    return schemas.OrderResponse(
        **order.__dict__,
        items=order_items
    )

@router.get("/", response_model=List[schemas.OrderResponse])
def get_orders(
    db: Session = Depends(get_db),
    current_user = Depends(auth.get_current_active_user)
):
    orders = crud.get_user_orders(db, current_user.id)
    result = []
    for order in orders:
        order_items = []
        for item in order.order_items:
            order_items.append({
                "product_name": item.product.name,
                "quantity": item.quantity,
                "size": item.size,
                "color": item.color,
                "price": item.price_at_time
            })
        result.append(schemas.OrderResponse(
            **order.__dict__,
            items=order_items
        ))
    return result