from fastapi import FastAPI, UploadFile, File
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import json
import os
import io
import base64
from pdf2image import convert_from_bytes
from schemas import Response
from validators import validate_dealercode, normalize_irncode, validate_hiibmispcode, normalize_gstin, validate_acknow, validate_irncode, validate_statecode, validate_hiibgstin, validate_dealergstin

load_dotenv()

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
    # try:
            read = await files.read()
            images = convert_from_bytes(read, poppler_path=r"C:\Program Files\poppler-26.02.0\Library\bin")
            for image in images:
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG")
                buffer.seek(0)
                base64_image = base64.b64encode(buffer.getvalue()).decode()
                prompt = """
                You are an expert PDF extractor
                Action: Perform extraction from the uploaded files:
                * General full forms: HIIB: Hyundia India Insurance Groking
                * Dealer means the person through whom dealing is being done
                * GSTIN: means GST number 
                * Consigner means dealer
                * Buyer means who is buying
                * Always compare the format with the index if it is different correct it right away.
                - irn:
                # Extract IRN value from the uploaded file
                # IRN is always exactly 64 hexadecimal characters (0-9, a-f)
                # Never include - while extracting IRN from file
                # if IRN value is divided into 2 lines like this: IRN :- fcae7936e5360de23b3d57c623b3743301bc0b786c5- then join both the values from both lines and remove -
                                                                         f43ed5fb9310ba9b972a5
                # IRN always appears at the very top of the invoice, labelled as "IRN:"
                # Never look for IRN downside it always the first line in the pdf uploaded.
                # Do NOT include any text from the address section (e.g. "Building No.9A") in the IRN
                # After joining, if the result is longer than 64 chars, take only the first 64 characters
                - ackno:
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
                - dealer_code:
                - hiib_misp_code:
                # It is always in the format of HIIB-MSY-XXXX where X represents digits.
                # Example: HIIB-MSY-9837
                - account_holders_name:
                - bank_name:
                - account_number:
                ~ If specifically account holder's name is mentioned with other bank details together then only extract and print its value.
                - branch:
                # Example: If it is mentioned as: G.T.ROAD PANIPAT & HDFC0000171
                            ~ Then G.T.ROAD PANIPAT is our branch name
                - bank_ifsc_code:
                # Example: If it is mentioned as: G.T.ROAD PANIPAT & HDFC0000171
                            ~ Then HDFC0000171 is our bank ifsc code
                - micr_code:
                - hiib_gstin:
                # Look for the column where Hyundia India Insurance Brooking is mentioned.
                # Extract HIIB GSTIN value
                # Example: 06AAGCH0310P1ZP format is: XXAAAAAXXXXAXAA where A represents alphabets and X represents digits.
                - dealer_gstin:
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

                - hiib_pincode:
                # Look for the column where Hyundia India Insurance Brooking is mentioned.
                # Identify the address and find the 6 digit pincode from it.
                # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                        J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                        Kanpur-208019
                    ~ Suppose this is the address then 208019 is the pincode
                - dealer_pincode:
                # Look for the column where Hyundia India Insurance is not mentioned.
                # Identify the pincode and find the 6 digit pincode from it and extract it.
                # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                        J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                        Kanpur-208019
                    ~ Suppose this is the address then 208019 is the pincode
                - hiib_state_code:
                # Always look for the column where Hyundia India Insurance Broking is written
                # After the column is identified look for the State Name 
                # After state name is identified there is a Code field written exactly beside the state name
                # Example: State Name: Haryana, Code: 06 
                    ~ Here, 06 is the state code
                - dealer_state_code:
                # Always look for the column where Hyundia India Insurance Broking is not written
                # After the column is identified look for the State Name 
                # After state name is identified there is a Code field written exactly beside the state name
                # Example: State Name: Haryana, Code: 06 
                    ~ Here, 06 is the state code
                - msme:
                - dealer_pan:
                # Always look for the column where Hyundia India Insurance Broking is not written
                # Dealer PAN means the person who is making this deal.
                # it must be inside the dealer column or the bill section
                # The person who is making this deal and we want PAN no. of that dealer.
                # Identify PAN and extract its value
                - sac:
                - consigner_details:
                # Always look for the column where Hyundia India Insurance Broking is not written
                # Extract its all details
                - consigner_address:
                # Always look for the column where Hyundia India Insurance Broking is not written
                # Extract its address
                - consigner_pincode:
                # Always look for the column where Hyundia India Insurance Broking is not written
                # Extract its 6 digit pincode
                - buyers_name:
                # Always look for the column where Hyundia India Insurance Broking is written
                # Identify its name and extract its value.
                - buyers_address:
                # Always look for the column where Hyundia India Insurance Broking is written
                # Identify its address and extract its value.
                - buyers_pincode:
                # Always look for the column where Hyundia India Insurance Broking is written
                # Identify its 6 digit pincode and extract its value.
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
                irn = content.get("irn")
                ackno = content.get("ackno")
                dealer = content.get("dealer_code")
                hiibmisp = content.get("hiib_misp_code")
                hiibstate = content.get("hiib_state_code")
                dealerstate = content.get("dealer_state_code")
                hiibgst = content.get("hiib_gstin")
                dealergstin = content.get("dealer_gstin")


                if irn:
                    irn = normalize_irncode(irn)
                    if not validate_irncode(irn):
                        print("retrying!")
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
                        print("retrying!")
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
                        print("retrying!")
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
                        print("retrying!")
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
                        print("retrying!")
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
                        print("retrying!")
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
                        print("retrying!")
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
                        print("retrying!")
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
                return content  # single-page PDF — return after processing first page
    # except:
    #     raise HTTPException(status_code=503, detail="API cannot be fetched. Try again later!!")
