import re
from typing import Tuple, Dict, Any

# Common character confusion pairs
DIGIT_TO_LETTER = {
    '0': 'O',
    '1': 'I',
    '2': 'Z',
    '4': 'A',
    '5': 'S',
    '6': 'G',
    '8': 'B'
}

LETTER_TO_DIGIT = {
    'O': '0',
    'D': '0',
    'Q': '0',
    'I': '1',
    'L': '1',
    'Z': '2',
    'A': '4',
    'S': '5',
    'G': '6',
    'B': '8'
}

def clean_raw_plate(raw_text: str) -> str:
    """Removes all whitespace, hyphens, periods, and special symbols, returning uppercase alphanumeric text."""
    if not raw_text:
        return ""
    # Strip spaces, hyphens, dots, special chars
    cleaned = re.sub(r'[^A-Za-z0-9]', '', str(raw_text)).upper()
    return cleaned

def normalize_indian_plate(raw_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Applies standard Indian RTO format positional corrections.
    Standard Format: SS DD LL DDDD (e.g. DL 01 AB 1234 or HR 26 D 4321)
    Bharat Series:   YY BH DDDD LL (e.g. 22 BH 1234 AA)
    """
    cleaned = clean_raw_plate(raw_text)
    if not cleaned:
        return "", {"corrections_made": 0, "original": raw_text}

    corrections_made = 0
    chars = list(cleaned)
    n = len(chars)

    # 1. Bharat series check: starts with 2 digits followed by 'BH'
    if n >= 9 and "".join(chars[2:4]) in ("BH", "8H", "B#", "8#"):
        # Position 0, 1: Digits (Year)
        for i in (0, 1):
            if chars[i] in LETTER_TO_DIGIT:
                chars[i] = LETTER_TO_DIGIT[chars[i]]
                corrections_made += 1
        chars[2] = 'B'
        chars[3] = 'H'
        # Position 4..7: Digits
        for i in range(4, min(8, n)):
            if chars[i] in LETTER_TO_DIGIT:
                chars[i] = LETTER_TO_DIGIT[chars[i]]
                corrections_made += 1
        # Position 8..n: Letters
        for i in range(8, n):
            if chars[i] in DIGIT_TO_LETTER:
                chars[i] = DIGIT_TO_LETTER[chars[i]]
                corrections_made += 1
        
        normalized = "".join(chars)
        return normalized, {"corrections_made": corrections_made, "schema": "BHARAT_SERIES"}

    # 2. Defence/Military series check: 2 digits + 1 letter + 6 digits + optional letter (e.g. 21D123456A)
    if re.match(r'^[0-9]{2}[A-Za-z][0-9]{5,7}[A-Za-z]?$', cleaned):
        # Keep digits at 0, 1 and letters at 2
        return cleaned, {"corrections_made": 0, "schema": "DEFENCE_BORDER"}

    # 3. Standard Indian RTO format: 
    # State Code (chars 0,1) -> Letters
    # RTO Code (chars 2,3) -> Digits
    # Series (chars 4 to n-4) -> Letters (1 to 3 chars)
    # Registration (last 4 chars) -> Digits
    if 8 <= n <= 11:
        # First 2 chars -> Letters
        for i in (0, 1):
            if chars[i] in DIGIT_TO_LETTER:
                chars[i] = DIGIT_TO_LETTER[chars[i]]
                corrections_made += 1
        
        # Next 1 or 2 chars (index 2,3 or index 2) -> Digits
        if n >= 9:
            for i in (2, 3):
                if chars[i] in LETTER_TO_DIGIT:
                    chars[i] = LETTER_TO_DIGIT[chars[i]]
                    corrections_made += 1
        
        # Last 4 chars -> Digits
        for i in range(n - 4, n):
            if chars[i] in LETTER_TO_DIGIT:
                chars[i] = LETTER_TO_DIGIT[chars[i]]
                corrections_made += 1

        # Middle series chars (between RTO digit and last 4 digits) -> Letters
        for i in range(4, n - 4):
            if chars[i] in DIGIT_TO_LETTER:
                chars[i] = DIGIT_TO_LETTER[chars[i]]
                corrections_made += 1

        normalized = "".join(chars)
        return normalized, {"corrections_made": corrections_made, "schema": "INDIAN_STANDARD"}

    return cleaned, {"corrections_made": 0, "schema": "GENERIC"}
