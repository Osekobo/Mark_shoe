from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    phone_number: str
    full_name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    role: str  # Will be "CUSTOMER" or "ADMIN" (uppercase)
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Product schemas
class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    category: str
    brand: str
    sizes: List[str]
    colors: List[str]
    images: List[str]
    stock_quantity: int

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    sizes: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    images: Optional[List[str]] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Cart schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: int
    size: str
    color: str

class CartItemCreate(CartItemBase):
    pass

class CartItemResponse(CartItemBase):
    id: int
    product: ProductResponse
    added_at: datetime
    
    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total: float

# Order schemas
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    size: str
    color: str

class OrderItemResponse(BaseModel):  # NEW - for better type safety
    product_name: str
    quantity: int
    size: str
    color: str
    price: float

class OrderCreate(BaseModel):
    shipping_address: str
    phone_number: str
    items: List[OrderItemCreate]

class OrderResponse(BaseModel):
    id: int
    order_number: str
    total_amount: float
    status: str  # "pending", "paid", "shipped", etc.
    payment_status: str  # "pending", "completed", "failed", "refunded"
    shipping_address: str
    phone_number: str
    created_at: datetime
    mpesa_receipt_number: Optional[str] = None
    items: List[OrderItemResponse]  # Improved from List[Dict[str, Any]]
    
    class Config:
        from_attributes = True

# M-Pesa schemas
class MpesaSTKPushRequest(BaseModel):
    phone_number: str
    amount: float
    order_id: int

class MpesaSTKPushResponse(BaseModel):
    MerchantRequestID: str
    CheckoutRequestID: str
    ResponseCode: str
    ResponseDescription: str
    CustomerMessage: str

class MpesaCallbackBody(BaseModel):
    Body: Dict[str, Any]