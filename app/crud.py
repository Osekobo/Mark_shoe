from sqlalchemy.orm import Session
from sqlalchemy import and_
import secrets
import string
from datetime import datetime

# Import specific classes from models
from .models import (
    User, Product, CartItem, Order, OrderItem, 
    MpesaTransaction, OrderStatus, PaymentStatus
)

# Import specific schemas (not the whole module)
from .schemas import (
    UserCreate, ProductCreate, CartItemCreate, OrderCreate
)

# Import auth function
from .auth import get_password_hash

# User CRUD
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_phone(db: Session, phone_number: str):
    return db.query(User).filter(User.phone_number == phone_number).first()

def create_user(db: Session, user: UserCreate):  # Changed from schemas.UserCreate to UserCreate
    # 🔍 DEBUG: inspect what is actually being passed
    print("DEBUG PASSWORD TYPE:", type(user.password))
    print("DEBUG PASSWORD VALUE:", repr(user.password))
    print("DEBUG PASSWORD LENGTH:", len(str(user.password)))

    # 🧠 Safety check (prevents bcrypt crash if bad input sneaks in)
    password = user.password

    if not isinstance(password, str):
        raise ValueError(f"Password must be a string, got {type(password)}")

    if len(password.encode("utf-8")) > 72:
        print("WARNING: password is longer than 72 bytes (bcrypt limit avoided via bcrypt_sha256)")

    # 🔐 Hash password safely
    hashed_password = get_password_hash(password)

    # 👤 Create DB user
    db_user = User(
        email=user.email,
        phone_number=user.phone_number,
        full_name=user.full_name,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

# Product CRUD
def get_products(db: Session, skip: int = 0, limit: int = 100, category: str = None):
    query = db.query(Product).filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category == category)
    return query.offset(skip).limit(limit).all()

def get_product(db: Session, product_id: int):
    return db.query(Product).filter(Product.id == product_id).first()

def create_product(db: Session, product: ProductCreate):  # Changed from schemas.ProductCreate
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product_stock(db: Session, product_id: int, quantity: int):
    product = get_product(db, product_id)
    if product:
        product.stock_quantity -= quantity
        db.commit()
        db.refresh(product)
    return product

# Cart CRUD
def get_cart_items(db: Session, user_id: int):
    return db.query(CartItem).filter(CartItem.user_id == user_id).all()

def add_to_cart(db: Session, user_id: int, item: CartItemCreate):  # Changed from schemas.CartItemCreate
    # Check if item already exists in cart
    existing_item = db.query(CartItem).filter(
        and_(
            CartItem.user_id == user_id,
            CartItem.product_id == item.product_id,
            CartItem.size == item.size,
            CartItem.color == item.color
        )
    ).first()
    
    if existing_item:
        existing_item.quantity += item.quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        db_item = CartItem(
            user_id=user_id,
            **item.dict()
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

def remove_from_cart(db: Session, cart_item_id: int, user_id: int):
    db.query(CartItem).filter(
        and_(
            CartItem.id == cart_item_id,
            CartItem.user_id == user_id
        )
    ).delete()
    db.commit()

def clear_cart(db: Session, user_id: int):
    db.query(CartItem).filter(CartItem.user_id == user_id).delete()
    db.commit()

# Order CRUD
def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"ORD-{timestamp}-{random_str}"

def create_order(db: Session, user_id: int, order_data: OrderCreate):  # Changed from schemas.OrderCreate
    # Calculate total amount
    total = 0
    order_items = []
    
    for item in order_data.items:
        product = get_product(db, item.product_id)
        if product:
            item_total = product.price * item.quantity
            total += item_total
            order_items.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "size": item.size,
                "color": item.color,
                "price_at_time": product.price
            })
    
    # Create order
    db_order = Order(
        order_number=generate_order_number(),
        user_id=user_id,
        total_amount=total,
        shipping_address=order_data.shipping_address,
        phone_number=order_data.phone_number,
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.PENDING
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items
    for item_data in order_items:
        db_order_item = OrderItem(
            order_id=db_order.id,
            **item_data
        )
        db.add(db_order_item)
        
        # Update product stock
        update_product_stock(db, item_data["product_id"], item_data["quantity"])
    
    db.commit()
    
    # Clear user's cart
    clear_cart(db, user_id)
    
    return db_order

def get_user_orders(db: Session, user_id: int):
    return db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()

def get_order(db: Session, order_id: int, user_id: int):
    return db.query(Order).filter(
        and_(
            Order.id == order_id,
            Order.user_id == user_id
        )
    ).first()

def update_order_payment(db: Session, order_id: int, mpesa_receipt: str, transaction_id: str, result_code: int):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        if result_code == 0:
            order.payment_status = PaymentStatus.COMPLETED
            order.status = OrderStatus.PAID
        else:
            order.payment_status = PaymentStatus.FAILED
        order.mpesa_receipt_number = mpesa_receipt
        order.mpesa_transaction_id = transaction_id
        order.mpesa_result_code = result_code
        db.commit()
        db.refresh(order)
    return order

def create_mpesa_transaction(db: Session, transaction_data: dict):
    db_transaction = MpesaTransaction(**transaction_data)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction