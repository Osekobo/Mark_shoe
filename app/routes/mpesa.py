from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from .. import schemas, crud, mpesa
from ..database import get_db
from ..config import settings
from ..models import User
from ..auth import get_current_active_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/stk-push")
async def initiate_payment(
    payment_data: schemas.MpesaSTKPushRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Initiate M-Pesa STK Push payment
    """
    # Verify order belongs to user
    order = crud.get_order(db, payment_data.order_id, current_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify order amount matches
    if order.total_amount != payment_data.amount:
        raise HTTPException(status_code=400, detail="Amount mismatch")
    
    # Verify order is pending payment
    if order.payment_status != "pending":
        raise HTTPException(status_code=400, detail="Order already processed")
    
    try:
        # Initiate STK Push
        response = await mpesa.mpesa_client.stk_push(
            phone_number=payment_data.phone_number,
            amount=payment_data.amount,
            account_reference=order.order_number,
            transaction_desc=f"Payment for Order {order.order_number}",
            callback_url=settings.MPESA_CALLBACK_URL
        )
        
        # Store transaction details
        transaction_data = {
            "order_id": order.id,
            "merchant_request_id": response.get("MerchantRequestID"),
            "checkout_request_id": response.get("CheckoutRequestID"),
            "amount": payment_data.amount,
            "phone_number": payment_data.phone_number
        }
        crud.create_mpesa_transaction(db, transaction_data)
        
        return response
        
    except Exception as e:
        logger.error(f"M-Pesa STK Push failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment initiation failed: {str(e)}")

@router.post("/callback")
async def mpesa_callback(
    callback_data: schemas.MpesaCallbackBody,
    db: Session = Depends(get_db)
):
    """
    M-Pesa STK Push Callback URL
    This endpoint is called by Safaricom after user completes payment
    """
    try:
        # Extract callback data
        body = callback_data.Body
        stk_callback = body.get("stkCallback", {})
        
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        
        # Find transaction
        transaction = db.query(crud.models.MpesaTransaction).filter(
            crud.models.MpesaTransaction.checkout_request_id == checkout_request_id
        ).first()
        
        if not transaction:
            logger.error(f"Transaction not found for CheckoutRequestID: {checkout_request_id}")
            return {"ResultCode": 1, "ResultDesc": "Transaction not found"}
        
        # Update transaction with result
        transaction.result_code = result_code
        transaction.result_desc = result_desc
        
        if result_code == 0:
            # Payment successful
            callback_metadata = stk_callback.get("CallbackMetadata", {})
            items = callback_metadata.get("Item", [])
            
            mpesa_receipt = None
            amount = None
            transaction_date = None
            
            for item in items:
                if item.get("Name") == "MpesaReceiptNumber":
                    mpesa_receipt = item.get("Value")
                elif item.get("Name") == "Amount":
                    amount = item.get("Value")
                elif item.get("Name") == "TransactionDate":
                    transaction_date = item.get("Value")
            
            transaction.mpesa_receipt_number = mpesa_receipt
            transaction.amount = amount
            if transaction_date:
                from datetime import datetime
                transaction.transaction_date = datetime.strptime(str(transaction_date), "%Y%m%d%H%M%S")
            
            # Update order payment status
            crud.update_order_payment(
                db,
                transaction.order_id,
                mpesa_receipt,
                checkout_request_id,
                result_code
            )
            
            logger.info(f"Payment successful for order {transaction.order_id}: {mpesa_receipt}")
        else:
            # Payment failed
            crud.update_order_payment(
                db,
                transaction.order_id,
                None,
                checkout_request_id,
                result_code
            )
            logger.error(f"Payment failed for order {transaction.order_id}: {result_desc}")
        
        db.commit()
        
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        return {"ResultCode": 1, "ResultDesc": str(e)}

@router.get("/query/{checkout_request_id}")
async def query_payment_status(
    checkout_request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Query the status of a payment
    """
    # Verify transaction belongs to user's order
    transaction = db.query(crud.models.MpesaTransaction).filter(
        crud.models.MpesaTransaction.checkout_request_id == checkout_request_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    order = crud.get_order(db, transaction.order_id, current_user.id)
    if not order:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        status = await mpesa.mpesa_client.query_status(checkout_request_id)
        return status
    except Exception as e:
        logger.error(f"Status query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Status query failed")