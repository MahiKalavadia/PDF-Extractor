import re

def normalize_irncode(irn: str) -> str:
    if not irn:
        return ""
    irn = irn.replace("-", "").replace(" ", "").replace("\n", "").strip().lower()
    irn = re.sub(r"[^0-9a-f]", "", irn)
    return irn


def validate_irncode(irn: str) -> bool:
    if not irn:
        return False
    return len(irn) == 64


def validate_acknow(ack: str) -> bool:
    return bool(re.fullmatch(r"[0-9]{15}", ack))


def validate_dealercode(code: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][0-9]{4}", code))


def validate_hiibmispcode(hiib: str) -> bool:
    return bool(re.fullmatch(r"HIIB[-\s]MHY-[0-9]{4}", hiib))


def validate_statecode(code: str) -> bool:
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
    gstin = normalize_gstin(gstin)
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][A-Z]{2}", gstin))


def validate_dealergstin(gstin: str) -> bool:
    gstin = normalize_gstin(gstin)
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9][A-Z][A-Z0-9]", gstin))
