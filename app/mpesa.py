import requests
import base64
from datetime import datetime
from typing import Dict, Any
import httpx
from .config import settings

class MpesaClient:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.environment = settings.MPESA_ENVIRONMENT
        
        if self.environment == "sandbox":
            self.base_url = "https://sandbox.safaricom.co.ke"
        else:
            self.base_url = "https://api.safaricom.co.ke"
    
    async def get_access_token(self) -> str:
        """Get OAuth access token from Safaricom"""
        auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                auth_url,
                headers={"Authorization": f"Basic {auth}"}
            )
            response.raise_for_status()
            return response.json()["access_token"]
    
    def generate_password(self) -> str:
        """Generate password for STK push"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        return password, timestamp
    
    async def stk_push(self, phone_number: str, amount: float, account_reference: str, 
                       transaction_desc: str, callback_url: str) -> Dict[str, Any]:
        """
        Initiate STK Push (Lipa Na M-Pesa Online API)
        """
        access_token = await self.get_access_token()
        password, timestamp = self.generate_password()
        
        # Format phone number (remove 0 or +254, add 254)
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif phone_number.startswith("+"):
            phone_number = phone_number[1:]
        
        stk_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(stk_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def query_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """Query the status of an STK Push transaction"""
        access_token = await self.get_access_token()
        password, timestamp = self.generate_password()
        
        query_url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(query_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

mpesa_client = MpesaClient()