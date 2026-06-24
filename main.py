from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import  re, Levenshtein, base64, json, os, io, logging, datetime
from dotenv import load_dotenv
from pdf2image import convert_from_bytes
from schemas import Response
from datetime import datetime
from validators import (
    validate_dealercode, validate_hiibmispcode, 
    validate_acknow, validate_irncode, validate_statecode, validate_hiibgstin,
    validate_dealergstin, validate_account_number 
)
from prompt import prompt
from extract_data import extract_all_qr_data

load_dotenv()

# Configure Poppler path dynamically from environment
POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\Program Files\poppler-26.02.0\Library\bin")
if POPPLER_PATH == "":
    POPPLER_PATH = None

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

log_filename = f"app_{datetime.today().strftime('%Y-%m-%d')}.log"
file_handler = logging.FileHandler(filename=os.path.join(LOG_DIR, log_filename))
file_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Content Extractor",
    description="Extract information from the pdf uploaded"
)

origins = [
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_headers = ["*"],
    allow_methods=["*"]
)

api_key = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=api_key)


@app.post("/information")
async def info(files:UploadFile=File(...)):
    """Extracting information from invoices pdf uploaded by user by first converting pdf to image 
    through pdf2image and then extracting data and added fallback to retry extracting some values if validation fails"""
    logger.info(f"Received file: {files.filename}")
    read = await files.read()
    images = convert_from_bytes(read, dpi=400, poppler_path=POPPLER_PATH)
    
    qr_irn, qr_invoice, qr_dealer_gstin, qr_hiib_gstin = extract_all_qr_data(images)
    if qr_irn:
        logger.info(f"QR IRN found: {qr_irn}")
    if qr_invoice:
        logger.info(f"QR Invoice found: {qr_invoice}")
    if qr_dealer_gstin:
        logger.info(f"QR Dealer GSTIN found: {qr_dealer_gstin}")
    if qr_hiib_gstin:
        logger.info(f"QR HIIB GSTIN found: {qr_hiib_gstin}")

    extracted_content = Response().model_dump()
    for page_no, image1 in enumerate(images, start=1):
        buffer = io.BytesIO()
        image1.save(buffer, format="JPEG")
        buffer.seek(0)
        base64_image = base64.b64encode(buffer.getvalue()).decode()
        logger.info(f"Page {page_no} converted to base64 image")

        response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role":"user",
                    "content":[{
                        "type":"text",
                        "text":prompt
                    },
                    {
                        "type":"image_url",
                        "image_url":{
                            "url":f"data:image/jpeg;base64,{base64_image}",
                        }
                    }]
                }],
                response_format={
                    "type":"json_schema",
                    "json_schema":{
                        "name":"extract_info",
                        "schema": Response.model_json_schema()
                    }
                }
            )
        content = json.loads(response.choices[0].message.content or "{}")
        logger.info(f"LLM extraction complete for file: {files.filename}")
        irn = content.get("irn")
        if qr_invoice:
            content["invoice_number"] = qr_invoice.upper()
        else:
            content["invoice_number"] = content.get("invoice_number", "")
        
        ackno = content.get("ack_no")
        dealer = content.get("dealer_code")
        hiibmisp = content.get("hiib_misp_code")
        hiibstate = content.get("hiib_state_code")
        dealerstate = content.get("dealer_state_code")
        hiibgst = content.get("hiib_gstin")
        dealergstin = content.get("dealer_gstin")
        account_number = content.get("account_number")

        if irn:
            llm_valid = validate_irncode(irn)
            qr_valid = validate_irncode(qr_irn) if qr_irn else False

            if qr_valid:
                if llm_valid:
                    distance = Levenshtein.distance(irn, qr_irn)
                    logger.info(f"Levenshtein distance LLM vs QR IRN: {distance}")

                    if distance == 0:
                        logger.info("IRN: LLM and QR match exactly")
                        content["irn"] = irn
                    elif 1 <= distance <= 3:
                        logger.info("IRN: Minor mismatch (distance 1-3), using QR value")
                        content["irn"] = qr_irn
                    else:
                        logger.warning("IRN: Major mismatch (distance > 3), clearing value")
                        content["irn"] = ""
                else:
                    logger.warning("LLM IRN invalid, using QR IRN")
                    content["irn"] = qr_irn
            else:
                content["irn"] = irn if llm_valid else ""

        else:
            content["irn"] = qr_irn if qr_irn and validate_irncode(qr_irn) else ""
       
        if ackno:
            ackno_norm = re.sub(r"[^\d]", "", str(ackno).strip())
            content["ack_no"] = ackno_norm if validate_acknow(ackno_norm) else ""
        else:
            content["ack_no"] = ""

        if dealer:
            dealer_norm = re.sub(r"[\s\-]", "", str(dealer).upper().strip())
            content["dealer_code"] = dealer_norm if validate_dealercode(dealer_norm) else ""
        else:
            content["dealer_code"] = ""

        if hiibmisp:
            if not validate_hiibmispcode(hiibmisp):
                logger.warning("Validation failed for hiib-misp-code!")
                content["hiib_misp_code"] = ""
            else:
                content["hiib_misp_code"] = hiibmisp
        else:
            content["hiib_misp_code"] = ""

        if hiibstate:
            if not validate_statecode(hiibstate):
                logger.warning("Validation failed for statecode!")
                content["hiib_state_code"] = ""
            else:
                content["hiib_state_code"] = hiibstate
        else:
            content["hiib_state_code"] = ""

        if dealerstate:
            if not validate_statecode(dealerstate):
                logger.warning("Validation failed for dealerstate!")
                content["dealer_state_code"] = ""
            else:
                content["dealer_state_code"] = dealerstate
        else:
            content["dealer_state_code"] = ""

        if hiibgst:
            content["hiib_gstin"] = hiibgst.upper() if isinstance(hiibgst, str) else hiibgst

            llm_valid = validate_hiibgstin(hiibgst)
            qr_valid = validate_hiibgstin(qr_hiib_gstin) if qr_hiib_gstin else False

            if qr_valid:
                if llm_valid:
                    distance = Levenshtein.distance(hiibgst.upper(), qr_hiib_gstin.upper())
                    logger.info(f"Levenshtein distance LLM vs QR hiibgst: {distance}")

                    if distance == 0:
                        logger.info("HIIB GSTIN: LLM and QR match exactly")
                        content["hiib_gstin"] = hiibgst.upper()
                    elif 1 <= distance <= 3:
                        logger.info("HIIB GSTIN: Minor mismatch (distance 1-3), using QR value")
                        content["hiib_gstin"] = qr_hiib_gstin.upper()
                    else:
                        logger.warning("HIIB GSTIN: Major mismatch (distance > 3), clearing value")
                        content["hiib_gstin"] = ""
                else:
                    logger.warning("LLM hiibgst invalid, using QR hiibgst")
                    content["hiib_gstin"] = qr_hiib_gstin.upper() if qr_hiib_gstin else ""
            else:
                content["hiib_gstin"] = hiibgst.upper() if llm_valid else ""

        else:
            content["hiib_gstin"] = qr_hiib_gstin.upper() if qr_hiib_gstin and validate_hiibgstin(qr_hiib_gstin) else ""

        if dealergstin:
            content["dealer_gstin"] = dealergstin.upper() if isinstance(dealergstin, str) else dealergstin

            llm_valid = validate_dealergstin(dealergstin)
            qr_valid = validate_dealergstin(qr_dealer_gstin) if qr_dealer_gstin else False

            if qr_valid:
                if llm_valid:
                    distance = Levenshtein.distance(dealergstin.upper(), qr_dealer_gstin.upper())
                    logger.info(f"Levenshtein distance LLM vs QR dealergst: {distance}")

                    if distance == 0:
                        logger.info("Dealer GSTIN: LLM and QR match exactly")
                        content["dealer_gstin"] = dealergstin.upper()
                    elif 1 <= distance <= 3:
                        logger.info("Dealer GSTIN: Minor mismatch (distance 1-3), using QR value")
                        content["dealer_gstin"] = qr_dealer_gstin.upper()
                    else:
                        logger.warning("Dealer GSTIN: Major mismatch (distance > 3), clearing value")
                        content["dealer_gstin"] = ""
                else:
                    logger.warning("LLM dealergst invalid, using QR dealergst")
                    content["dealer_gstin"] = qr_dealer_gstin.upper() if qr_dealer_gstin else ""
            else:
                content["dealer_gstin"] = dealergstin.upper() if llm_valid else ""

        else:
            content["dealer_gstin"] = qr_dealer_gstin if qr_dealer_gstin and validate_dealergstin(qr_dealer_gstin) else ""

        if account_number:
            if not validate_account_number(account_number):
                logger.warning("Validation failed for account number!")
                content["account_number"] = ""
            else:
                content["account_number"] = account_number
        else:
            content["hiib_state_code"] = ""

        for key, value in content.items():
            if value:
                current_val = extracted_content.get(key)
                if current_val == "" or current_val == 0.0 or current_val == 0:
                    extracted_content[key] = value
                else:
                    logger.info(f"Field '{key}' is already set (value: {current_val})")

    return extracted_content
