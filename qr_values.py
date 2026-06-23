import jwt, json, re
import logging

logger = logging.getLogger(__name__)

def decode_data(text:str) -> dict:
    if not text:
        return {}
    
    text = text.strip()
    
    try:
        outer = jwt.decode(text, options={"verify_signature":False})
        logger.info(f"JWT outer keys: {list(outer.keys())}")

        data = outer.get("data","")
        if data:
            if isinstance(data, str):
                try:
                    inner = json.loads(data)
                except Exception:
                    inner = {}
            else:
                inner = data
            return inner
    except (jwt.exceptions.InvalidTokenError, jwt.exceptions.DecodeError) as e:
        logger.warning(f"JWT decode error: {e}")
    except Exception as e:
        logger.warning(f"Error parsing decoded JWT: {e}")
    return {}


def find_irn(text: str) -> str:
    """Extract IRN from QR text — handles NIC e-Invoice JWT, JSON, or raw IRN."""
    text = text.strip()
    inner = decode_data(text)
    irn = inner.get("Irn") or inner.get("irn", "")
    if not irn:
        match = re.search(r"\b([0-9a-fA-F]{64})\b", text)
        if match:
            irn = match.group(1)
    if irn and len(irn) == 64:
        logger.info(f"IRN found: {irn}")
        return irn.lower()

def find_invno(text: str) -> str:
    """Extract InvoiceNumber from QR text — handles NIC e-Invoice JWT or JSON."""
    text = text.strip()
    inner = decode_data(text)
    invoice = inner.get("DocNo") or inner.get("docno")
    if invoice :
        logger.info(f"Invoice found in nested data: {invoice}")
        return invoice.lower()

def find_dealergst(text: str) -> str:
    """Extract Dealergstin from QR text — handles NIC e-Invoice JWT, JSON, or raw GSTIN."""
    text = text.strip()
    inner = decode_data(text)
    dealergst = inner.get("SellerGstin") or inner.get("sellergstin")
    if not dealergst:
        # Check if the raw text contains a valid GSTIN pattern
        match = re.search(r"\b([0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z][0-9a-zA-Z]{3})\b", text)
        if match:
            dealergst = match.group(1)
    if dealergst :
        logger.info(f"Seller Gstin found: {dealergst}")
        return dealergst.lower()

def find_hiibgst(text: str) -> str:
    """Extract BuyerGstin from QR text — only handles e-invoice JWT or JSON to avoid misattributing single GSTIN."""
    text = text.strip()
    inner = decode_data(text)
    hiibgst = inner.get("BuyerGstin") or inner.get("buyergstin")
    if hiibgst :
        logger.info(f"Buyer Gstin found in nested data: {hiibgst}")
        return hiibgst.lower()