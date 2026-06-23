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
    """Validating statecode to be of length 2"""
    if not code:
        return ""
    match = re.search(r"\d+", str(code))
    if match:
        num_str = match.group(0)
        if len(num_str) == 1:
            return "0" + num_str
        elif len(num_str) == 2:
            return num_str
    return bool(re.fullmatch(r"[0-9]{2}", str(code)))

def normalize_gstin(gstin: str) -> str:
    """
    Fix 0/O and 1/I confusion using GSTIN positional structure.
    Format: DD AAAAA DDDD A D A A  (D=digit, A=alphabet)
    Positions:
      digits : 0,1, 7,8,9,10, 12
      alpha  : 2,3,4,5,6, 11, 13,14

    Also strips any extra characters so length is exactly 15.
    """
    if not gstin:
        return ""
    gstin = gstin.upper().replace(" ", "").replace("\n", "").replace("-", "").strip()
    gstin = re.sub(r"[^A-Z0-9]", "", gstin)

    if len(gstin) != 15:
        return gstin

    DIGIT_FIX = {"O": "0", "I": "1", "Z": "2", "B": "8", "S": "5"}
    ALPHA_FIX = {"0": "O", "1": "I", "2": "Z", "8": "B", "5": "S"}

    DIGIT_POS = {0, 1, 7, 8, 9, 10, 12}
    ALPHA_POS = {2, 3, 4, 5, 6, 11, 13, 14}

    result = []
    for i, ch in enumerate(gstin):
        if i in DIGIT_POS:
            result.append(DIGIT_FIX.get(ch, ch))
        elif i in ALPHA_POS:
            result.append(ALPHA_FIX.get(ch, ch))
        else:
            result.append(ch)
    return "".join(result)


def validate_hiibgstin(gstin: str) -> bool:
    """Validating hiib gstin to be of exact length 15"""
    gstin = normalize_gstin(gstin)
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][A-Z]{2}", gstin))


def validate_dealergstin(gstin: str) -> bool:
    """Validating dealer gstin of length 15"""
    gstin = normalize_gstin(gstin)
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][A-Z][A-Z0-9]", gstin))


def validate_account_number(acc: str) -> bool:
    """validating account number to be in length between 9-18 and removing spaces or hypens to check"""
    if not acc:
        return ""
    acc_str = str(acc).strip()
    if acc_str.endswith(".0"):
        acc_str = acc_str[:-2]
    acc_str = re.sub(r"[^\d]", "", acc_str)
    acc = re.sub(r"[\s\-]", "", acc)
    return bool(re.fullmatch(r"[0-9]{9,18}", acc))

# def normalize_hiibmispcode(code: str) -> str:
#     """Normalize HIIB MISP code to standard HIIB-MHY-XXXX format."""
#     if not code:
#         return ""
#     code = code.strip().upper()
#     code = re.sub(r"[\s\-]+", "-", code)
#     if code.startswith("MHY-"):
#         code = "HIIB-" + code
#     return code


# def normalize_statecode(code: str) -> str:
#     """Extract numeric state code and zero-pad to 2 digits if single-digit."""
#     if not code:
#         return ""
#     match = re.search(r"\d+", str(code))
#     if match:
#         num_str = match.group(0)
#         if len(num_str) == 1:
#             return "0" + num_str
#         elif len(num_str) == 2:
#             return num_str
#     return ""


# def normalize_account_number(acc: str) -> str:
#     """Remove spaces, hyphens, non-digits, and trailing .0 from account numbers."""
#     if not acc:
#         return ""
#     acc_str = str(acc).strip()
#     if acc_str.endswith(".0"):
#         acc_str = acc_str[:-2]
#     acc_str = re.sub(r"[^\d]", "", acc_str)
#     return acc_str
