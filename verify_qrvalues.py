import logging
import re
from validators import validate_irncode, validate_hiibgstin, validate_dealergstin

logger = logging.getLogger(__name__)

def verify_qr_data(qr_data:str) -> str:
    if not qr_data:
        logger.warning("QR Data verification failed!")
        return ""
    return qr_data
    
def verify_qr_irn(qr_irn: str) -> bool:
    """Verify the IRN extracted from QR is a valid 64-char hex string."""
    qr_irn = verify_qr_data(qr_irn)
    is_valid = validate_irncode(qr_irn)
    if is_valid:
        logger.info(f"QR IRN verified: {qr_irn}")
    else:
        logger.warning(f"QR IRN invalid (len={len(qr_irn)}): {qr_irn}")
    return is_valid

# def verify_qr_invoice(qr_inv: str) -> bool:
#     """Verify the IRN extracted from QR is a valid 64-char hex string."""
#     if not qr_inv:
#         logger.warning("QR Invoice verification failed: empty value")
#         return False
#     else:
#         logger.info(f"QR Invoice verified: {qr_inv}")
#         return qr_inv

def verify_qr_dealergst(qr_dealergst: str) -> bool:
    """Verify the IRN extracted from QR is a valid 64-char hex string."""
    qr_dealergst = verify_qr_data(qr_dealergst)
    is_valid = validate_dealergstin(qr_dealergst)
    if is_valid:
        logger.info(f"QR SellerGstin verified: {qr_dealergst}")
    else:
        logger.warning(f"QR SellerGstin invalid (len={len(qr_dealergst)}): {qr_dealergst}")
    return is_valid

def verify_qr_hiibgst(qr_hiibgst: str) -> bool:
    """Verify the IRN extracted from QR is a valid 64-char hex string."""
    qr_hiibgst = verify_qr_data(qr_hiibgst)
    is_valid = validate_hiibgstin(qr_hiibgst)
    if is_valid:
        logger.info(f"QR HiibGstin verified: {qr_hiibgst}")
    else:
        logger.warning(f"QR HiibGstin invalid (len={len(qr_hiibgst)}): {qr_hiibgst}")
    return is_valid