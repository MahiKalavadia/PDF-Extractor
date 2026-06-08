import re

def validate_irncode(irn: str):
    """Normalize and validate IRN: ensure only alphanumeric characters remain and non-empty."""
    if not irn:
        return False
    irn_norm = normalize_irncode(irn)
    return bool(irn_norm) and irn_norm.isalnum()

def validate_acknow(ack:str):
    """Validating Acknowlegemnt No. which is extracted to match its pattern."""
    regex = r"[0-9]{15}"
    pattern = re.compile(regex)

    if re.match(pattern, ack) and len(ack) == 15:
        return True
    else:
        return False
    
def validate_dealercode(code:str):
    """Validating dealer code which is extracted to match its pattern"""
    regex = r"[A-Z]{1}[0-9]{4}"
    pattern = re.compile(regex)
    
    if re.match(pattern, code) and len(code) == 5:
        return True
    else:
        return False
    
def validate_hiibmispcode(hiib:str):
    """Validating HIIB Misp Code which is extracted to match its pattern"""
    regex= r"HIIB-MHY-[0-9]{4}"
    regex2 = r"HIIB MHY-[0-9]{4}"

    pattern = re.compile(regex)
    pattern2 = re.compile(regex2)

    if re.match(pattern,hiib):
        return True
    elif re.match(pattern2, hiib):
        return True
    else:
        return False
    
def validate_hiibstatecode(code:str):
    """Validating HIIB State Code which is extracted to match its pattern"""
    regex = r"[0-9]{2}"
    pattern = re.compile(regex)
    if re.match(pattern, code):
        return True
    else:
        return False
    
def validate_dealerstatecode(code:str):
    """Validating State Code which is extracted to match its pattern"""
    regex = r"[0-9]{2}"
    pattern = re.compile(regex)
    if re.match(pattern, code):
        return True
    else:
        return False
    
def validate_hiibgstin(gstin:str):
    """Validating HIIB GSTIN which is extracted to match its pattern"""
    if gstin:
        return True
    else:
        return False

def normalize_irncode(irn: str):
    """Remove hyphens, whitespace and any non-alphanumeric characters from IRN."""
    if irn is None:
        return ""
    # Remove any character that is not A-Z, a-z, or 0-9
    cleaned = re.sub(r'[^A-Za-z0-9]', '', irn)
    return cleaned.strip()