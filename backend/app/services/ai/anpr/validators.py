import re
from typing import Optional, Dict, Any, List
from app.services.ai.anpr.base import ValidationOutcome
from app.services.ai.anpr.normalizer import normalize_indian_plate, clean_raw_plate

# All valid Indian States & Union Territories RTO 2-letter codes
INDIAN_STATE_CODES = {
    "AN", # Andaman and Nicobar Islands
    "AP", # Andhra Pradesh
    "AR", # Arunachal Pradesh
    "AS", # Assam
    "BR", # Bihar
    "CG", # Chhattisgarh
    "CH", # Chandigarh
    "DD", # Daman and Diu
    "DL", # Delhi
    "DN", # Dadra and Nagar Haveli
    "GA", # Goa
    "GJ", # Gujarat
    "HP", # Himachal Pradesh
    "HR", # Haryana
    "JH", # Jharkhand
    "JK", # Jammu and Kashmir
    "KA", # Karnataka
    "KL", # Kerala
    "LA", # Ladakh
    "LD", # Lakshadweep
    "MH", # Maharashtra
    "ML", # Meghalaya
    "MN", # Manipur
    "MP", # Madhya Pradesh
    "MZ", # Mizoram
    "NL", # Nagaland
    "OD", # Odisha (OR previously)
    "OR", # Odisha (legacy)
    "PB", # Punjab
    "PY", # Puducherry
    "RJ", # Rajasthan
    "SK", # Sikkim
    "TN", # Tamil Nadu
    "TR", # Tripura
    "TS", # Telangana
    "UK", # Uttarakhand (UA previously)
    "UA", # Uttarakhand (legacy)
    "UP", # Uttar Pradesh
    "WB"  # West Bengal
}

# Regex patterns
RE_INDIAN_STANDARD = re.compile(r'^([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{4})$')
RE_BHARAT_SERIES = re.compile(r'^([0-9]{2})BH([0-9]{4})([A-Z]{1,2})$')
RE_DEFENCE_BORDER = re.compile(r'^([0-9]{2})([A-Z])([0-9]{6})([A-Z]?)$')
RE_GENERIC_ALPHANUMERIC = re.compile(r'^[A-Z0-9]{5,12}$')

class IndianPlateValidator:
    """Production validator for Indian license plates across Standard RTO, Bharat Series, and Defence formats."""

    @staticmethod
    def validate(raw_plate: str) -> ValidationOutcome:
        if not raw_plate:
            return ValidationOutcome(
                status="INVALID",
                format_name="UNKNOWN",
                confidence=0.0,
                diagnostics="Empty plate string provided"
            )

        normalized, norm_meta = normalize_indian_plate(raw_plate)
        if len(normalized) < 5 or len(normalized) > 12:
            return ValidationOutcome(
                status="INVALID",
                format_name="UNKNOWN",
                confidence=0.0,
                diagnostics=f"Length {len(normalized)} out of bounds (expected 5-12 chars)"
            )

        # 1. Check Bharat Series (e.g. 22BH1234AA)
        bh_match = RE_BHARAT_SERIES.match(normalized)
        if bh_match:
            year_prefix = int(bh_match.group(1))
            # BH series started in 2021 (21BH..)
            if 20 <= year_prefix <= 35:
                return ValidationOutcome(
                    status="VALID",
                    format_name="BHARAT_SERIES",
                    confidence=0.98,
                    diagnostics=f"Valid Bharat Series (Year: 20{year_prefix}, Series: {bh_match.group(3)})"
                )

        # 2. Check Standard Indian RTO Format (e.g. DL01AB1234, MH12DE1432, HR26DK8392)
        std_match = RE_INDIAN_STANDARD.match(normalized)
        if std_match:
            state_code = std_match.group(1)
            rto_num = std_match.group(2)
            series_code = std_match.group(3)
            reg_num = std_match.group(4)

            if state_code in INDIAN_STATE_CODES:
                return ValidationOutcome(
                    status="VALID",
                    format_name="INDIAN_STANDARD",
                    confidence=0.95,
                    diagnostics=f"Valid Indian RTO: State={state_code}, RTO={rto_num}, Series={series_code}, Reg={reg_num}"
                )
            else:
                # Format matches syntax but state code is unknown
                return ValidationOutcome(
                    status="UNCERTAIN",
                    format_name="INDIAN_STANDARD_UNVERIFIED_STATE",
                    confidence=0.65,
                    diagnostics=f"Standard format syntax with unverified state code: {state_code}"
                )

        # 3. Check Defence / Military Format (e.g. 21D123456A)
        def_match = RE_DEFENCE_BORDER.match(normalized)
        if def_match:
            return ValidationOutcome(
                status="VALID",
                format_name="DEFENCE_BORDER",
                confidence=0.90,
                diagnostics=f"Valid Defence/Military registration vehicle format"
            )

        # 4. Fallback Generic Alphanumeric Check (Border/Special/VIP)
        if RE_GENERIC_ALPHANUMERIC.match(normalized):
            return ValidationOutcome(
                status="UNCERTAIN",
                format_name="NON_STANDARD_ALPHANUMERIC",
                confidence=0.50,
                diagnostics="Non-standard alphanumeric structure; valid characters but non-matching RTO regex"
            )

        return ValidationOutcome(
            status="INVALID",
            format_name="UNKNOWN",
            confidence=0.10,
            diagnostics="Does not match any known registration structure"
        )
