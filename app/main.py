from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from .database import engine, Base  # Changed from app.database to .database
from .routes import auth, products, cart, orders, mpesa  # Changed to .routes
from .config import settings  # Changed to .config

# Create database tables
Base.metadata.create_all(bind=engine)
# Base.metadata.drop_all(bind=engine)

app = FastAPI(
    title="Shoe Store API - Kenya",
    description="E-commerce API with M-Pesa integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(mpesa.router, prefix="/api/mpesa", tags=["M-Pesa"])

@app.get("/")
def root():
    return {
        "message": "Welcome to Shoe Store API - Kenya",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}