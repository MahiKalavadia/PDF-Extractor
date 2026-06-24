import re

def validate_irncode(irn: str) -> bool:
    """Validating irn code after it is normalised"""
    if not irn:
        return False
    irn = irn.replace("-", "").replace(" ", "").replace("\n", "").strip().lower()
    irn = re.sub(r"[^0-9a-f]", "", irn)
    return len(irn) == 64

def validate_acknow(ack: str) -> bool:
    """Validating acknowledgment number to match"""
    return bool(re.fullmatch(r"[0-9]{15}", ack))

def validate_dealercode(code: str) -> bool:
    """Validating dealercode to be of length 5"""
    a = re.compile(r"[A-Z][0-9]{4}")
    b = re.compile(r"[A-Z]{1}[0-9]{1}[A-Z]{1}[0-9]{2}")
    if re.search(a, code):
        return True
    elif re.search(b, code):
        return True
    else:
        return False

def validate_hiibmispcode(hiib: str) -> bool:
    """validating hiib misp code from extracted value to compare that if it is of same length"""
    if not hiib:
        return ""
    hiib = hiib.strip().upper()
    hiib = re.sub(r"[\s\-]+", "-", hiib)
    if hiib.startswith("MHY-"):
        hiib = "HIIB-" + hiib
    return bool(re.fullmatch(r"HIIB-MHY-[0-9]{4}", hiib))

def validate_statecode(code: str) -> bool:
    """Validating state code to be of length 2"""
    if not code:
        return False

    code = str(code).strip()

    if code.isdigit() and len(code) == 1:
        code = "0" + code

    return bool(re.fullmatch(r"\d{2}", code))


def validate_hiibgstin(gstin: str) -> bool:
    """Validating hiib gstin to be of exact length 15"""
    if not gstin:
        return ""
    gstin = str(gstin).strip().upper()
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][A-Z]{2}", gstin))


def validate_dealergstin(gstin: str) -> bool:
    """Validating dealer gstin of length 15"""
    if not gstin:
        return ""
    gstin = str(gstin).strip().upper()
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][A-Z][A-Z0-9]", gstin))


def validate_account_number(acc: str) -> bool:
    """validating account number to be in length between 9-18 and removing spaces or hypens to check"""
    if not acc:
        return ""
    acc_str = str(acc).strip()
    acc_str = re.sub(r"[^\d]", "", acc_str)
    return bool(re.fullmatch(r"[0-9]{9,18}", acc))

