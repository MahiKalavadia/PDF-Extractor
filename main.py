from fastapi import FastAPI, UploadFile, File
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import cv2, re
import Levenshtein
import numpy as np
from pyzbar.pyzbar import decode
from dotenv import load_dotenv
import json, os, io, logging
from logging.handlers import RotatingFileHandler
import base64
from pdf2image import convert_from_bytes
from schemas import Response
from validators import validate_dealercode, normalize_irncode, validate_hiibmispcode, normalize_gstin, validate_acknow, validate_irncode, validate_statecode, validate_hiibgstin, validate_dealergstin

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

@app.post("/information")
async def info(files:UploadFile=File(...)):
            logger.info(f"Received file: {files.filename}")
            read = await files.read()
            images = convert_from_bytes(read, dpi=400,poppler_path=r"C:\Program Files\poppler-26.02.0\Library\bin")
            open_cv_image = np.array(images[0])
            gray_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
            decoded_objects = decode(gray_image)
            qr_data = decoded_objects[0].data.decode('utf-8')
            irn_match = re.search(r"[a-fA-F0-9]{64}", qr_data)
            for page_no, image in enumerate(images,start=1):
                print(f"Processing page {page_no}")
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG")
                buffer.seek(0)
                base64_image = base64.b64encode(buffer.getvalue()).decode()
                prompt = """
                You are an expert PDF extractor.

                Action: Perform extraction from the uploaded files.

                General Instructions:

                - HIIB means Hyundai India Insurance Broking.
                - Dealer means the person/company through whom dealing is being done.
                - GSTIN means GST number.
                - Consigner means Dealer.
                - Buyer means Hyundai India Insurance Broking unless explicitly mentioned otherwise.
                - Carefully read all pages, tables, headers, footers, GST sections, bank details sections and billing tables.
                - Always cross check OCR errors such as O/0, I/1, G/6, Z/2, B/8 before finalizing values.
                - Always compare extracted values with their expected format and correct OCR mistakes only when required.
                - Return ONLY valid JSON.
                - Do not return explanations.
                - Do not return markdown.
                - Do not return notes.
                - If a field is not extracted or not present inside do not show it in output
                - Always return all fields.
                - Never print same field name twice.
                - Never calculate any amount explicitly. Extract only values that are present.

                Fields:
                - irn:
                IRN Extraction Rules:
                - Search the entire document for labels such as:
                IRN
                Invoice Reference Number
                Invoice Ref No
                - IRN is always a 64-character hexadecimal string.
                - If IRN is split across multiple lines, concatenate all consecutive hexadecimal fragments until a 64-character value is formed.
                - Ignore spaces, line breaks, hyphens (-), colons (:), and other separators while constructing the IRN.
                - If multiple candidate IRNs are found, choose the one closest to the IRN label.
                - Before returning, verify:
                1. Length must be exactly 64 characters.
                2. Only characters 0-9 and a-f are allowed.
                3. Remove any non-hexadecimal characters.
                4. Never misinterpret any character with different character
                - If a valid 64-character IRN can be reconstructed from adjacent fragments, return it instead of an empty string.
                - ack_no:
                - Example: 123246152465342
                - ack_date:
                - Return format DD-MM-YYYY.
                - Convert month names into month numbers.
                - Jan=01 Feb=02 Mar=03 Apr=04 May=05 Jun=06 Jul=07 Aug=08 Sep=09 Oct=10 Nov=11 Dec=12
                - invoice_number:
                - invoice_date:
                - Return format DD-MM-YYYY.
                - Convert month names into month numbers.
                - Jan=01 Feb=02 Mar=03 Apr=04 May=05 Jun=06 Jul=07 Aug=08 Sep=09 Oct=10 Nov=11 Dec=12
                - taxable_value:
                - Taxable value means amount before GST.
                - cgst_amount:
                - sgst_amount:
                - igst_amount:
                - total_invoice:
                - Amount after adding all GST taxes.
                - dealer_code: Look at the compressed value where words are sticked.
                - hiib_misp_code:
                - It can even be mentioned as MISP Code:
                - It can be as MSY-0847 so add HIIB ahead
                - Format: HIIB-MSY-XXXX
                - Example: HIIB-MSY-9837
                - account_holders_name:
                - Inside company's bank detail section
                - Extract only if present with bank details section.
                - Account holders name must be present with other bank details.
                - If ac. holders name not found then print empty string ""
                - bank_name:
                - account_number:
                - branch:
                - Example:
                    G.T.ROAD PANIPAT & HDFC0000171
                    Branch = G.T.ROAD PANIPAT
                - bank_ifsc_code: IFS Code or IFSC Code
                - Example:
                    G.T.ROAD PANIPAT & HDFC0000171
                    IFSC = HDFC0000171
                - micr_code:
                - hiib_gstin:
                - Extract GSTIN belonging to Hyundai India Insurance Broking.
                - GSTIN format must be XXAAAAAXXXXAXAA.
                - Correct OCR mistakes only if required to match GSTIN format.
                - dealer_gstin:
                - Extract GSTIN belonging to Dealer.
                - Usually present in column where Buyer(Bill To) is not written.
                - GSTIN format must be XXAAAAAXXXXAXAA.
                - Digit positions: 0,1,7,8,9,10,11,13
                - Alphabet positions: 2,3,4,5,6,12,14
                - Correct OCR mistakes if required:
                    O→0
                    I→1
                    Z→2
                    B→8
                - hiib_pincode:
                - Identify Hyundai India Insurance Broking address and extract 6 digit pincode.
                - dealer_pincode:
                - Identify Dealer address and extract 6 digit pincode.
                - hiib_state_code:
                - Look in Hyundai India Insurance Broking section.
                - Example:
                    State Name: Haryana
                    Code: 06
                    Output: 06
                - dealer_state_code:
                - Look in Dealer section.
                - Example:
                    State Name: Haryana
                    Code: 06
                    Output: 06
                - msme:
                - dealer_pan:
                - sac:
                - Extract SAC code from invoice.
                - consigner_details:
                - Look for Consignee To section.
                - Extract complete details.
                - consigner_address:
                - Look for Consignee To section.
                - Extract address only.
                - consigner_pincode:
                - Look for Consignee To section.
                - Extract 6 digit pincode.
                - buyers_name:
                - Extract Hyundai India Insurance Broking name.
                - buyers_address:
                - Extract Hyundai India Insurance Broking address.
                - buyers_pincode:
                - Extract Hyundai India Insurance Broking pincode.
                - consigner_place_of_supply:
                - Extract city/place from Dealer/Consigner address.
                - buyer_place_of_supply:
                - Extract city/place from Buyer address.
                - description_of_service:
                - Must be extracted from billing/service table.
                - oem:
                - quantity:
                - First look for Quantity column in billing table.
                - If Quantity column exists, extract its value.
                - If Quantity column does not exist, count total service/item rows from billing table.
                - Look for the table and inside table look for sr no and look how many quantity it bought
                - period_of_service:
                - Extract service period if available.

                Return output strictly in this JSON format:

                {
                "irn": "",
                "ack_no": "",
                "ack_date": "",
                "invoice_no": "",
                "invoice_date": "",
                "taxable_value": "",
                "cgst_amount": "",
                "sgst_amount": "",
                "igst_amount": "",
                "total_invoice_value": "",
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
                "msme_code": "",
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
                        logger.warning("Validation failed for irn, retrying!")
                        irn_prompt = """
                        Extract only IRN value from the file
                        Rules:
                        - return json
                        - remove whitespaces, hypens 
                        - Length of IRN must be 64
                        - Do not include any extra character
                        - If irn cannot be identified return:
                        - if IRN value is divided into 2 lines like this: IRN :- fcae7936e5360de23b3d57c623b3743301bc0b786c5- then join both the values from both lines and remove -
                                                                                 f43ed5fb9310ba9b972a5
                        - Never include (-) inside the extracted string
                        {"irn":""}
                        """
                        retry_response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[{
                                "role":"user",
                                "content":[{
                                    "type":"text",
                                    "text":irn_prompt
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
                                    "name":"extract_irn",
                                    "schema":{
                                        "type":"object",
                                        "properties":{
                                            "irn":{"type":"string"}
                                        },
                                        "required":["irn"]
                                    }
                                }
                            }
                        )
                        retry_content = json.loads(retry_response.choices[0].message.content or "{}")
                        fallback_irn = retry_content.get("irn", "")
                        fallback_irn = normalize_irncode(fallback_irn)
                        if fallback_irn == irn_match:
                            content["irn"] == fallback_irn
                        else:
                            content["irn"] == irn_match
                        if validate_irncode(fallback_irn):
                            content["irn"] = fallback_irn
                        else:
                            content["irn"] = ""
                    else:
                        content["irn"] = irn
                else:
                    content["irn"] = ""
                        
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
                return content  
