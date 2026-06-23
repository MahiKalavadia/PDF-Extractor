from qreader import QReader
import logging
from qr_values import find_dealergst, find_hiibgst, find_invno, find_irn
import numpy as np

logger = logging.getLogger(__name__)


def extract_all_qr_data(images) -> tuple:
    """Scan all page images for QR codes once and extract IRN, Invoice Number, Seller GSTIN, and Buyer GSTIN."""
    qr_irn = ""
    qr_invoice = ""
    qr_dealer_gstin = ""
    qr_hiib_gstin = ""
    
    try:
        qreader = QReader()
        for idx, img in enumerate(images, start=1):
            image_np = np.array(img)
            decoded_texts = qreader.detect_and_decode(image=image_np)
            if decoded_texts:
                logger.info(f"Page {idx}: QReader detected {len(decoded_texts)} objects")
                for text in decoded_texts:
                    if text:
                        if not qr_irn:
                            qr_irn = find_irn(text) or ""
                        if not qr_invoice:
                            qr_invoice = find_invno(text) or ""
                        if not qr_dealer_gstin:
                            qr_dealer_gstin = find_dealergst(text) or ""
                        if not qr_hiib_gstin:
                            qr_hiib_gstin = find_hiibgst(text) or ""
            else:
                logger.info(f"Page {idx}: No QR codes detected")
    except Exception as e:
        logger.warning(f"QR scanning failed: {e}")
        
    return qr_irn, qr_invoice, qr_dealer_gstin, qr_hiib_gstin
