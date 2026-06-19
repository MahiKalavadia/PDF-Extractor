from fastapi import FastAPI, UploadFile, File
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import cv2, re
import Levenshtein
import numpy as np
from qreader import QReader
from pyzbar.pyzbar import decode as pyzbar_decode
from dotenv import load_dotenv
import json, os, io, logging
from logging.handlers import RotatingFileHandler
import base64
from pdf2image import convert_from_bytes
from schemas import Response
from validators import validate_dealercode, normalize_irncode, validate_hiibmispcode, normalize_gstin, validate_acknow, validate_irncode, validate_statecode, validate_hiibgstin, validate_dealergstin, validate_account_number

load_dotenv()

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

file_handler = RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8"
)

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

def find_irn(text: str) -> str:
        """Finding irn value inside"""
        if not text:
            return ""
        m = re.search(r'[0-9a-fA-F]{64}', text)
        if m:
            return m.group().lower()
        return ""

def extract_irn_from_qr(pil_image) -> str:
    """Extracting irn after scanning qr code from image"""
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    try:
        for obj in pyzbar_decode(gray):
            raw = obj.data.decode("utf-8", errors="ignore")
            irn = find_irn(raw)
            if irn:
                logger.info(f"IRN from pyzbar: {irn}")
                return irn
    except Exception as e:
        logger.warning(f"pyzbar failed: {e}")
    return ""

prompt ="""
                You are an expert PDF extractor
                    Action: Perform extraction from the uploaded files:
                    * General full forms: HIIB: Hyundia India Insurance Groking
                    * Dealer means the person through whom dealing is being done
                    * GSTIN: means GST number 
                    * Consigner means dealer
                    * Buyer means who is buying
                    * Aways cross check triple times between ocr like identify if it is 0 or O , 1 or I , 6 or G, 2 or Z like that.
                    * Always compare the format with the index if it is different correct it right away.
                    - irn:
                    # Extract IRN value from the uploaded file
                    - irn: 64-char hex string (0-9, a-f only). Concatenate fragments across line breaks. Verify length=64 before returning.
                    - **Example**: b2d026b6df33f699fa486efd04fe322c6d-    -> concetenate both into a single line
                                53dd6ffbe72dc6f709f0f031449c9f
                    - ack_no:  ~15-digit acknowledgement number
                    # Example : "123246152465342"
                    - ack_date: Date should always be in this format : DD-MM-YYYY
                    # If month is written as name like may jun jul then convert it into month number
                    # Jan - 01, Feb - 02, Mar - 03, Apr - 04, may - 05, Jun - 06, Jul - 07, Aug - 08, Sep - 09, Oct - 10, Nov - 11, Dec - 12
                    - invoice_number:
                    - invoice_date: Date should always be in this format : DD-MM-YYYY
                    # If month is written as name like may jun jul then convert it into month number
                    # Jan - 01, Feb - 02, Mar - 03, Apr - 04, may - 05, Jun - 06, Jul - 07, Aug - 08, Sep - 09, Oct - 10, Nov - 11, Dec - 12

                    - taxable_value:
                    # Look for the taxable value in the invoice and print its value
                    # taxable value means the price before gst price is added
                    - cgst_amount: 
                    - sgst_amount:
                    - igst_amount:
                    - total_invoice_value:
                    # Amount after GST value added is the total invoice value.
                    - dealer_code: look for compressed/concatenated values or mentioned as DEALER CODE
                    - hiib_misp_code:
                    - format HIIB-MHY-XXXX. If found as MHY-XXXX, prepend "HIIB-"
                    - it can be mentioned as HIIB-MISP-Code or HIIB-MISP or MISP-code
                    ### Bank details
                    Example: Company's Bank details
                    Ac. Holders name: NATASHA AUTOMOBILES PRIVATE LIMITED
                    Bank Name: Bank of Baroda-105
                    Ac no: 30490500000105
                    Branch and IFS/IFSC Code: IZZA ITANAGAR BAREILLY & BARB0IZZATN
                    # - account_holders_name: Search for the section containing bank details and extract ac holders name if available
                        - Here in example above, NATASHA AUTOMOBILES PRIVATE LIMITED is ac holders name
                    # - bank_name:
                        - Here, in example above, Bank of Baroda-105 is bank name.
                    # - account_number:
                        - Here in the example above, 30490500000105 is the account number
                    # - branch:
                        - Here in the example above, IZZA ITANAGAR BAREILLY is our branch name
                    # - bank_ifsc_code:
                        - Here in the example above, BARB0IZZATN is our bank ifsc code
                    - micr_code:
                    - hiib_gstin:
                    # GSTIN in HIIB section
                    # Look for the column where Hyundia India Insurance Brooking is mentioned.
                    # Extract HIIB GSTIN value
                    # Example: 06AAGCH0310P1ZP format is: XXAAAAAXXXXAXAA where A represents alphabets and X represents digits.
                    - dealer_gstin:
                    # GSTIN in dealer/consigner section (not Buyer/Bill To) Look for the section where Buyer Bill to is not written and extract GSTIN or UIN 
                    # Look at the column which doesnt have written Buyer(bill to)
                    # Extract Dealer's GSTIN value
                    # Compare index and its value extracted if digit index has extracted alphabet value then correct it and if alphabet index has extracted digit value then correct it. In next line i have providedwith correction.
                    # It is always in the format of XXAAAAAXXXXAXAA where A represents alphabets and X represents digits
                    # So now after extracting check what was extracted and in which format. 
                    # Digits will be in index: { 0, 1, 7, 8, 9, 10, 11, 13 }
                    # Alphabets must be in index: { 2, 3, 4, 5, 6, 12, 14 }
                    # If any digit index contains alphabets look here and correct it: {"0":"O", "1":"I","2":"Z","8":"B"}
                    # If any alphabet index contains digits look here and correct it: {"O":"0", "I":"1", "Z":"2", "B":"8"}
                    # Match the index with the extracted value
                    # Example: 07ABCCS3697R1ZE

                    **hiib_pincode**: 6-digit pin from HIIB address
                    - **Example: SHRI GANGA VEHICLES PVT LTD
                                NEAR DTO OFFICE, JAIPUR ROAD, CHURU,
                                Churu, Rajasthan, 331001
                                GSTIN/UIN: 08AALCS3285P1ZH
                                State Name : Rajasthan, Code : 08
                                E-Mail : shrigangahyundaichuru@gmail.com
                        - Look for the section where Buyer(Bill to) and Hyundia India Insurance Brooking is written and extract hiib_pincode here 331001 is hiib_pincode
                    - **dealer_pincode**: 6-digit pin from dealer address
                    - **Example: SHRI GANGA VEHICLES PVT LTD
                                NEAR DTO OFFICE, JAIPUR ROAD, CHURU,
                                Churu, Rajasthan, 331001
                                GSTIN/UIN: 08AALCS3285P1ZH
                                State Name : Rajasthan, Code : 08
                                E-Mail : shrigangahyundaichuru@gmail.com
                        - Look for the section where Buyer(Bill to) is not written and extract dealer_pincode here 331001 is dealer_pincode
                    - **hiib_state_code**: numeric code from HIIB section (e.g. "06")
                    - **Example: SHRI GANGA VEHICLES PVT LTD
                                NEAR DTO OFFICE, JAIPUR ROAD, CHURU,
                                Churu, Rajasthan, 331001
                                GSTIN/UIN: 08AALCS3285P1ZH
                                State Name : Rajasthan, Code : 08
                                E-Mail : shrigangahyundaichuru@gmail.com
                                - Look for the HIIB secton(Hyundia India Insurance Brooking) and extract state code. here in example above , state code is 08
                    - **dealer_state_code**: numeric code from dealer section
                    - **Example: SHRI GANGA VEHICLES PVT LTD
                                NEAR DTO OFFICE, JAIPUR ROAD, CHURU,
                                Churu, Rajasthan, 331001
                                GSTIN/UIN: 08AALCS3285P1ZH
                                State Name : Rajasthan, Code : 08
                                E-Mail : shrigangahyundaichuru@gmail.com
                                - Look for the state code inside the dealer section. here in example above , state code is 08
                    - msme: if split across lines, concatenate
                    - dealer_pan:
                    - sac:
                **Service Provider:
                Example:
                Consignee (Ship to)
                HYUNDAI INDIA INSURANCE BROKING PRIVATE LTD
                16th Floor, Building No. 9A, DLF Cyber City, DLF
                Phase-III, Gurugram - 122001
                GSTIN/UIN : 06AAGCH0310P1ZP
                PAN/IT No : AAGCH0310P
                State Name : Haryana, Code : 06
                    - consigner_details:
                    - They are service providers
                    # Look for the section where Consignee (Ship to) is written and identify its details and extract it
                    # In the above example:  HYUNDAI INDIA INSURANCE BROKING PRIVATE LTD
                                            16th Floor, Building No. 9A, DLF Cyber City, DLF
                                            Phase-III, Gurugram - 122001 this is the consignee details
                    - consigner_address:
                    They are service providers
                    # Look for the section where Consignee (Ship to) is written and identify its address and extract it
                    # In the example above, 16th Floor, Building No. 9A, DLF Cyber City, DLF
                                            Phase-III, Gurugram - 122001 this is the consignee address
                    - consigner_pincode:
                    They are service providers
                    # Look for the section where Consignee (Ship to) is written and identify its 6 digit pincode inside address and extract it
                    # In the example above, 122001 is the consignee pincode
                **Buyer
                - Example: 
                Buyer (Bill to)
                HYUNDAI INDIA INSURANCE BROKING PRIVATE LTD
                16th Floor, Building No. 9A, DLF Cyber City, DLF
                Phase-III, Gurugram - 122001
                GSTIN/UIN : 06AAGCH0310P1ZP
                PAN/IT No : AAGCH0310P
                State Name : Haryana, Code : 06
                *** Always look for the column/section where buyer (bill to ) is written
                    - buyers_name:
                    # Always look for the column where Buyer (Bill to) Hyundia India Insurance Broking is written
                    # Identify its name and extract its value.
                    # In the example above, HYUNDAI INDIA INSURANCE BROKING PRIVATE LTD is the buyers name
                    - buyers_address:
                    # Always look for the column where Hyundia India Insurance Broking is written
                    # Identify its address and extract its value.
                    - In the example above, 16th Floor, Building No. 9A, DLF Cyber City, DLF
                    Phase-III, Gurugram - 122001 is the buyers address
                    - buyers_pincode:
                    # Always look for the column where Hyundia India Insurance Broking is written
                    # Identify its 6 digit pincode and extract its value.
                    # In the example above, 122001 is the buyers pincode
                    - consigner_place_of_supply:
                    # In which place the dealer is supplying the goods from.
                    # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                            J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                            Kanpur-208019
                        ~ Suppose this is the address then Kanpur is the consigner place of supply
                    - consigner_place_of_buyer:
                    # In which place he buyer is receiving its goods.
                    # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                            J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                            Kanpur-208019
                        ~ Suppose this is the address then Kanpur is the buyer's place of supply
                    - description:
                    # must be inside the billing table 
                    - oem:
                    # can be also written OEM or OEM code or oem
                    - quantity:
                    # Look at the bill section and identify the sr no. column
                                ~ After the sr no. column is identified look at how many sr no. are there.
                                ~ and count the number of sr no. there
                                Example: Sr no.
                                        1
                                        ~ Here Quantity is 1
                                Example 2: Sr no.
                                            2
                                        ~ here quantity is 2
                    - period_of_service:
                    Rules:
                    - Print every field names and if the information about the specific field is not available then return empty string.
                    - If some information is not available in pdf then print empty string.
                    - Dont add extra fields which are not getting extracted.
                    - Dont even add that field name whose value is not present
                    - If field values are not getting extracted dont even print its field name
                    ## Output Format

                    Return this exact JSON structure:

                    {
                    "irn": "",
                    "ack_no": "",
                    "ack_date": "",
                    "invoice_number": "",
                    "invoice_date": "",
                    "taxable_value": "",
                    "cgst_amount": "",
                    "sgst_amount": "",
                    "igst_amount": "",
                    "total_invoice": "",
                    "dealer_code": "",
                    "hiib_misp_code": "",
                    "account_holders_name": "",
                    "bank_name": "",
                    "account_number": "",
                    "branch": "",
                    "bank_ifsc_code": "",
                    "micr_code": "",
                    "hiib_gstin": "",
                    "dealer_gstin": "",
                    "hiib_pincode": "",
                    "dealer_pincode": "",
                    "hiib_state_code": "",
                    "dealer_state_code": "",
                    "msme": "",
                    "dealer_pan": "",
                    "sac": "",
                    "consigner_details": "",
                    "consigner_address": "",
                    "consigner_pincode": "",
                    "buyers_name": "",
                    "buyers_address": "",
                    "buyers_pincode": "",
                    "consigner_place_of_supply": "",
                    "buyer_place_of_supply": "",
                    "description_of_service": "",
                    "oem": "",
                    "quantity": "",
                    "period_of_service": ""
                    }
                """

@app.post("/information")
async def info(files:UploadFile=File(...)):
            """Extracting information from invoices pdf uploaded by user by first converting pdf to image 
            through pdf2image and then extracting data and added fallback to retry extracting some values if validation fails"""
            logger.info(f"Received file: {files.filename}")
            read = await files.read()
            images = convert_from_bytes(read, dpi=400, poppler_path=r"C:\Program Files\poppler-26.02.0\Library\bin")
            qr_irn = ""
            for img in images:
                qr_irn = extract_irn_from_qr(img)
                if qr_irn:
                    logger.info(f"QR IRN found : {qr_irn}")
                    break
            logger.info(f"QR IRN: {qr_irn or 'not found'}")

            extracted_content = {}
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
                ackno = content.get("ack_no")
                dealer = content.get("dealer_code")
                hiibmisp = content.get("hiib_misp_code")
                hiibstate = content.get("hiib_state_code")
                dealerstate = content.get("dealer_state_code")
                hiibgst = content.get("hiib_gstin")
                dealergstin = content.get("dealer_gstin")

                if irn:
                    irn = normalize_irncode(irn)
                    if not validate_irncode(irn):
                        logger.warning("Validation failed for IRN, retrying!")
                        irn_prompt = """
                        Extract only IRN value from the file
                        Rules:
                        - return json
                        - remove whitespaces, hyphens
                        - Length of IRN must be 64
                        - Do not include any extra character
                        - if IRN value is divided into 2 lines join both and remove -
                        - Never include (-) inside the extracted string
                        {"irn":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": irn_prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }],
                            response_format={
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "extract_irn",
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "irn": {"type": "string"}
                                        },
                                        "required": ["irn"]
                                    }
                                }
                            }
                        )

                        retry_content = json.loads(
                            retry_response.choices[0].message.content or "{}"
                        )
                        irn = normalize_irncode(retry_content.get("irn", ""))

                    llm_valid = validate_irncode(irn)
                    qr_valid = validate_irncode(qr_irn) if qr_irn else False

                    if qr_valid:
                        if llm_valid:
                            distance = Levenshtein.distance(irn, qr_irn)
                            logger.info(f"Levenshtein distance LLM vs QR IRN: {distance}")

                            if distance == 0:
                                logger.info("IRN: LLM and QR match")
                                content["irn"] = irn
                            else:
                                logger.warning(
                                    f"IRN mismatch (distance={distance}), using QR value"
                                )
                                content["irn"] = qr_irn
                        else:
                            logger.warning("LLM IRN invalid, using QR IRN")
                            content["irn"] = qr_irn
                    else:
                        content["irn"] = irn if llm_valid else ""

                else:
                    content["irn"] = qr_irn if qr_irn and validate_irncode(qr_irn) else ""
               
                        
                if ackno:
                    if not validate_acknow(ackno):
                        logger.warning("Validation failed for extracting ackno, retrying!")
                        ackno_prompt = """
                        Extract only Ack No. from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of ackno. must be 15
                        - Do not include any extra character
                        - If ackno. cannot be identified return:
                        {"ackno":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":ackno_prompt
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
                                    "name":"extract_ackno",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "ackno":{"type":"string"}
                                        },
                                        "required":["ackno"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content)
                        fallback_ackno = retry_content.get("ackno","")
                        if validate_acknow(fallback_ackno):
                            content["ackno"] = fallback_ackno
                        else:
                            content["ackno"] = ""
                else:
                    content["ackno"] = ""

                if dealer:
                    if not validate_dealercode(dealer):
                        logger.warning("Validation failed for dealercode, retrying!")
                        dealer_prompt = """
                        Extract only Dealer Code value from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of dealer code must be 5
                        - Do not include any extra character
                        - If dealer code cannot be identified return:
                        {"dealer_code":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":dealer_prompt
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
                                    "name":"extract_dealercode",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "dealer_code":{"type":"string"}
                                        },
                                        "required":["dealer_code"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content)
                        fallback_dealer = retry_content.get("dealer_code","")
                        if validate_dealercode(fallback_dealer):
                            content["dealer_code"] = fallback_dealer
                        else:
                            content["dealer_code"] = ""
                else:
                    content["dealer_code"] = ""

                if hiibmisp:
                    if not validate_hiibmispcode(hiibmisp):
                        logger.warning("Validation failed for hiib-misp-code, retrying!")
                        hiibmisp_prompt = """
                        Extract only HIIB MISP value from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of HIIB MISP must be 13
                        - Do not include any extra character
                        - If HIIB MISP cannot be identified return:
                        {"hiib_misp_code":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":hiibmisp_prompt
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
                                    "name":"extract_hiibmisp",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "hiib_misp_code":{"type":"string"}
                                        },
                                        "required":["hiib_misp_code"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content)
                        fallback_hiib_misp_code = retry_content.get("hiib_misp_code","")
                        if validate_hiibmispcode(fallback_hiib_misp_code):
                            content["hiib_misp_code"] = fallback_hiib_misp_code
                        else:
                            content["hiib_misp_code"] = ""
                else:
                    content["hiib_misp_code"] = ""

                if hiibstate:
                    if not validate_statecode(hiibstate):
                        logger.warning("Validation failed for statecode, retrying!")
                        hiibstate_prompt = """
                        Extract only state code from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of state code must be 2.
                        - Do not include any extra character
                        - If hiib state code cannot be identified return:
                        {"hiib_state_code":""}
                        - Example: State Name: Haryana, Code: 06 
                    ~ Here, 06 is the state code
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":hiibstate_prompt
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
                                    "name":"extract_hiib_state_code",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "hiib_state_code":{"type":"string"}
                                        },
                                        "required":["hiib_state_code"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content)
                        fallback_hiib_state_code = retry_content.get("hiib_state_code","")
                        if validate_statecode(fallback_hiib_state_code):
                            content["hiib_state_code"] = fallback_hiib_state_code
                        else:
                            content["hiib_state_code"] = ""
                else:
                    content["hiib_state_code"] = ""

                if dealerstate:
                    if not validate_statecode(dealerstate):
                        logger.warning("Validation failed for dealerstate, retrying!")
                        dealerstate_prompt = """
                        Extract only dealer state code value from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of dealer state code must be 2
                        - Do not include any extra character
                        - If irn cannot be identified return:
                        {"dealer_state_code":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":dealerstate_prompt
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
                                    "name":"extract_dealer_state_code",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "dealer_state_code":{"type":"string"}
                                        },
                                        "required":["dealer_state_code"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content)
                        fallback_dealer_state_code = retry_content.get("dealer_state_code","")
                        if validate_statecode(fallback_dealer_state_code):
                            content["dealer_state_code"] = fallback_dealer_state_code
                        else:
                            content["dealer_state_code"] = ""
                else:
                    content["dealer_state_code"] = ""

                if hiibgst:
                    hiibgst = normalize_gstin(hiibgst)
                    content["hiib_gstin"] = hiibgst
                    if not validate_hiibgstin(hiibgst):
                        logger.warning("Validation failed for hiib-gstin, retrying!")
                        gst_prompt = """
                        Extract only HIIB GSTIN value from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of HIIB GSTIN must be 15
                        - Make sure you differentiate between 0 and O
                        - Do not include any extra character
                        - If hiib gstin cannot be identified return:
                        {"hiib_gstin":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":gst_prompt
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
                                    "name":"extract_hiib_gstin",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "hiib_gstin":{"type":"string"}
                                        },
                                        "required":["hiib_gstin"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content)
                        fallback_hiib_gstin = retry_content.get("hiib_gstin","")
                        fallback_hiib_gstin = normalize_gstin(fallback_hiib_gstin)
                        content["hiib_gstin"] = fallback_hiib_gstin
                        if validate_hiibgstin(fallback_hiib_gstin):
                            content["hiib_gstin"] = fallback_hiib_gstin
                        else:
                            content["hiib_gstin"] = ""
                else:
                    content["hiib_gstin"] = ""

                if dealergstin:
                    dealergstin = normalize_gstin(dealergstin)
                    content["dealer_gstin"] = dealergstin
                    if not validate_dealergstin(dealergstin):
                        logger.warning("Validation failed for dealer-gstin, retrying!")
                        gstin_prompt = """
                        Extract only Dealer gstin value from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of dealer GSTIN must be 15
                        - Do not include any extra character
                        - Make sure you differentiate between 0 and O
                        - Separate alphabets properly and digits properlyy look at your database and see how digits are written from 0 to 9 and alphabets from A to Z.
                        - The difference in 0 and O is like 0 is number and O is alphabet. the circle which has line in between is 0 a digit or else a O an alphabet.
                        - Alphabets: A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
                        - Digits: 0 1 2 3 4 5 6 7 8 9
                        - Idetify the difference between 1 and I properly
                        - If dealer gstin cannot be identified return:
                        {"dealer_gstin":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":gstin_prompt
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
                                    "name":"extract_dealer_gstin",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "dealer_gstin":{"type":"string"}
                                        },
                                        "required":["dealer_gstin"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content)
                        fallback_dealer_gstin = retry_content.get("dealer_gstin","")
                        fallback_dealer_gstin = normalize_gstin(fallback_dealer_gstin)
                        content["dealer_gstin"] = fallback_dealer_gstin
                        if validate_dealergstin(fallback_dealer_gstin):
                            content["dealer_gstin"] = fallback_dealer_gstin
                        else:
                            content["dealer_gstin"] = ""
                else:
                    content["dealer_gstin"] = ""


                account_number = content.get("account_number", "")
                if account_number:
                    account_number = re.sub(r"[\s\-]", "", str(account_number))
                    content["account_number"] = account_number
                    if not validate_account_number(account_number):
                        logger.warning(f"Account number invalid ({account_number}), retrying!")
                        acc_prompt = """
                        Extract only the bank account number from the file.
                        Rules:
                        - return json
                        - Remove all spaces, hyphens
                        - Account number contains digits only
                        - Length is between 9 and 18 digits
                        - Do not include IFSC, MICR or any other code
                        - If not found return: {"account_number": ""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": acc_prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }],
                            response_format={
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "extract_account_number",
                                    "schema": {
                                        "type": "object",
                                        "properties": {"account_number": {"type": "string"}},
                                        "required": ["account_number"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content or "{}")
                        fallback_acc = re.sub(r"[\s\-]", "", retry_content.get("account_number", ""))
                        content["account_number"] = fallback_acc if validate_account_number(fallback_acc) else ""

                for key, value in content.items():
                    if value and not extracted_content.get(key):
                        extracted_content[key] = value 
                        logger.info(f"If pages and if data appending to extracted_content")
                    logger.info(f"No data to append!")

            return extracted_content
