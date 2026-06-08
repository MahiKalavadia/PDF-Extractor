from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
import json
import os
import io
import base64
from pdf2image import convert_from_bytes
from validators import validate_dealercode, validate_hiibmispcode, validate_acknow, validate_irncode, normalize_irncode, validate_dealerstatecode, validate_hiibgstin, validate_hiibstatecode

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
    read = await files.read()
    images = convert_from_bytes(read, poppler_path=r"C:\Program Files\poppler-26.02.0\Library\bin")
    for image in images:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")

        base64_image = base64.b64encode(buffer.getvalue()).decode()
        prompt = """
        Action: Perform extraction from the uploaded files:
        * General full forms: HIIB: Hyundia India Insurance Groking
        * Dealer means the person through whom dealing is being done
        * GSTIN: means GST number 
        * Consigner means dealer
        * Buyer means who is buying
        - IRN:
          # Never include any extra character or number.
          # Before printing always perform str.replace("-","")
          # Never extract whitespace or hyphen from the file
          # If length extracted is greater than 64 then recheck the extraction and the input file and identify what character or digit is extracted extra and never include that extra character or digit.
        - Ack No:
          # Example : "123246152465342"
        - Ack Date: Date should always be in this format : DD-MM-YYYY
        - Invoice Number:
        - Invoice Date: Date should always be in this format : DD-MM-YYYY
        - Taxable Value:
          # Look for the taxable value in the invoice and print its value
          # taxable value means the price before gst price is added
        - CGST Amount:
        - SGST Amount:
        - IGST Amount:
        - Total Invoice Value:
          # Amount after GST value added is the total invoice value.
        - Dealer Code:
        - HIIB MISP Code:
          # It is always in the format of HIIB-MSY-XXXX where X represents digits.
          # Example: HIIB-MSY-9837
        - Account holder's name:
        - Bank Name:
        - Account Number:
        - Branch:
        - Bank-IFSC Code:
        - MICR_code:
        - HIIB GSTIN/UIN:
          # Look for the column where Hyundia India Insurance Brooking is mentioned.
          # Extract HIIB GSTIN value
        - Dealer GSTIN:
          # Look at the column which doesnt have written Buyer(bill to)
          # Extract Dealer's GSTIN value
        - HIIB Pincode:
          # Look for the column where Hyundia India Insurance Brooking is mentioned.
          # Identify the address and find the 6 digit pincode from it.
          # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                Kanpur-208019
            ~ Suppose this is the address then 208019 is the pincode
        - Dealer Pincode:
          # Look for the column where Hyundia India Insurance is not mentioned.
          # Identify the pincode and find the 6 digit pincode from it and extract it.
          # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                Kanpur-208019
            ~ Suppose this is the address then 208019 is the pincode
        - HIIB State Code:
          # Always look for the column where Hyundia India Insurance Broking is written
          # After the column is identified look for the State Name 
          # After state name is identified there is a Code field written exactly beside the state name
          # Example: State Name: Haryana, Code: 06 
             ~ Here, 06 is the state code
        - Dealer State Code:
          # Always look for the column where Hyundia India Insurance Broking is not written
          # After the column is identified look for the State Name 
          # After state name is identified there is a Code field written exactly beside the state name
          # Example: State Name: Haryana, Code: 06 
             ~ Here, 06 is the state code
        - MSME:
        - Dealer PAN:
          # Always look for the column where Hyundia India Insurance Broking is not written
          # Identify PAN and extract its value
        - SAC:
        - Consigner details:
          # Always look for the column where Hyundia India Insurance Broking is not written
          # Extract its all details
        - Consigner address:
          # Always look for the column where Hyundia India Insurance Broking is not written
          # Extract its address
        - Consigner pincode:
          # Always look for the column where Hyundia India Insurance Broking is not written
          # Extract its 6 digit pincode
        - Buyer's name:
          # Always look for the column where Hyundia India Insurance Broking is written
          # Identify its name and extract its value.
        - Buyer's address:
          # Always look for the column where Hyundia India Insurance Broking is written
          # Identify its address and extract its value.
        - Buyer's pincode:
          # Always look for the column where Hyundia India Insurance Broking is written
          # Identify its 6 digit pincode and extract its value.
        - Consigner place of supply:
          # In which place the dealer is supplying the goods from.
          # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                Kanpur-208019
            ~ Suppose this is the address then Kanpur is the consigner place of supply
        - Buyer's place of supply:
          # In which place he buyer is receiving its goods.
          # Example: Khanna Auto Sales Pvt. Ltd. (Keshavpuram)
                                J/Comm-10,Keshavpuram Yojna No.01,Kalyanpur
                                Kanpur-208019
            ~ Suppose this is the address then Kanpur is the buyer's place of supply
        - Description:
        - Oem:
        - Quantity:
          # Look at the bill section and identify the sr no. column
                    ~ After the sr no. column is identified look at how many sr no. are there.
                    ~ and count the number of sr no. there
                    Example: Sr no.
                            1
                            ~ Here Quantity is 1
                    Example 2: Sr no.
                                2
                            ~ here quantity is 2
        - Period of Service:
        Rules:
        - Extract only those information which are available in pdf dont extract those information which are not present only.
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
                         "type": "json_schema",
                         "json_schema": {
                                 "name": "extracting_invoice_details",
                                 "schema": {
                                         "type": "object",
                                         "properties": {
                                                 "IRN": {"type": "string"},
                                                 "ACK No.": {"type": "string"},
                                                 "ACK Date": {"type": "string"},
                                                 "Invoice No.": {"type": "string"},
                                                 "Invoice Date": {"type": "string"},
                                                 "Taxable Value": {"type": "number"},
                                                 "CGST Amount": {"type": "number"},
                                                 "SGST Amount": {"type": "number"},
                                                 "IGST Amount": {"type": "number"},
                                                 "Total Invoice": {"type": "number"},
                                                 "Dealer Code": {"type": "string"},
                                                 "HIIB MISP Code": {"type": "string"},
                                                 "Account holder's name": {"type": "string"},
                                                 "Bank Name": {"type": "string"},
                                                 "Account Number": {"type": "integer"},
                                                 "Branch": {"type": "string"},
                                                 "Bank IFSC Code": {"type": "string"},
                                                 "MICR Code": {"type": "string"},
                                                 "HIIB GSTIN/UIN": {"type": "string"},
                                                 "Dealer Pincode": {"type": "string"},
                                                 "HIIB State Code": {"type": "string"},
                                                 "Dealer State Code": {"type": "string"},
                                                 "MSME": {"type": "string"},
                                                 "Dealer PAN": {"type": "string"},
                                                 "SAC": {"type": "string"},
                                                 "Consigner Name": {"type": "string"},
                                                 "Consigner Address": {"type": "string"},
                                                 "Consigner Pincode": {"type": "string"},
                                                 "Buyer's Name": {"type": "string"},
                                                 "Buyer's Address": {"type": "string"},
                                                 "Buyer's Pincode": {"type": "string"},
                                                 "Consigner place of supply": {"type": "string"},
                                                 "Consigner place of buyer": {"type": "string"},
                                                 "Description": {"type": "string"},
                                                 "Oem": {"type": "string"},
                                                 "Quantity": {"type": "integer"},
                                                 "Period of Service": {"type": "string"}
                                         },
                                          "required": ["IRN","ACK No.","ACK Date","Invoice No.","Invoice Date","Taxable Value","CGST Amount","SGST Amount","IGST Amount",
                                                       "Total Invoice","Dealer Code","HIIB MISP Code","Account holder's name","Bank Name","Account Number","Branch","Bank IFSC Code",
                                                       "MICR Code","HIIB GSTIN/UIN","Dealer Pincode","HIIB State Code","Dealer State Code","MSME","Dealer PAN","SAC",
                                                       "Consigner Name","Consigner Address","Consigner Pincode","Buyer's Name","Buyer's Address","Buyer's Pincode","Consigner place of supply",
                                                       "Consigner place of buyer","Description","Oem","Quantity","Period of Service"],
                                          "additionalProperties": False
                                 }
                         }
                 }
        )
        content = json.loads(response.choices[0].message.content)
        irn = content.get("IRN")
        ackno = content.get("ACK No.")
        dealer = content.get("Dealer Code")
        hiibmisp = content.get("HIIB MISP Code")
        hiibstate = content.get("HIIB State Code")
        dealerstate = content.get("Dealer State Code")
        hiibgst = content.get("HIIB GSTIN/UIN")

        if irn:
            irn = normalize_irncode(irn)
            if not validate_irncode(irn):
                return "IRN Code extracted is not valid!"
            content["IRN"] = irn
        if ackno:
            if not validate_acknow(ackno):
                return "Acknowledgment No. extarcted is not valid!"
        if dealer:
            if not validate_dealercode(dealer):
                return "Dealer Code extracted is not valid!"
        if hiibmisp:
            if not validate_hiibmispcode(hiibmisp):
                return "HIIB MISP extracted is not valid!"
        if hiibstate:
            if not validate_hiibstatecode(hiibstate):
                return "HIIB State Code extracted is not valid!"
        if dealerstate:
            if not validate_dealerstatecode(dealerstate):
                return "Dealer State Code extracted is not valid!"
        if hiibgst:
            if not validate_hiibgstin(hiibgst):
                return "HIIB GSTIN extracted is not valid!"
        return content