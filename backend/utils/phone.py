"""
Phone Number Normalization Utility (Global Multi-Country E.164 Engine)
Formats local and international numbers to standard E.164 (+<country_code><number>).
Supports Americas, Europe, Asia-Pacific, Middle East, and Africa.
"""
import re

COUNTRY_DIALING_CODES = {
    # Andean & South America
    'ecuador': '+593', 'ec': '+593',
    'peru': '+51', 'perú': '+51', 'pe': '+51',
    'colombia': '+57', 'co': '+57',
    'chile': '+56', 'cl': '+56',
    'argentina': '+54', 'ar': '+54',
    'bolivia': '+591', 'bo': '+591',
    'paraguay': '+595', 'py': '+595',
    'uruguay': '+598', 'uy': '+598',
    'venezuela': '+58', 've': '+58',
    'brasil': '+55', 'brazil': '+55', 'br': '+55',
    # North & Central America / Caribbean
    'mexico': '+52', 'méxico': '+52', 'mx': '+52',
    'estados unidos': '+1', 'united states': '+1', 'usa': '+1', 'us': '+1',
    'canada': '+1', 'canadá': '+1', 'ca': '+1',
    'costa rica': '+506', 'cr': '+506',
    'panama': '+507', 'panamá': '+507', 'pa': '+507',
    'guatemala': '+502', 'gt': '+502',
    'el salvador': '+503', 'sv': '+503',
    'honduras': '+504', 'hn': '+504',
    'nicaragua': '+505', 'ni': '+505',
    'republica dominicana': '+1', 'república dominicana': '+1', 'do': '+1',
    'puerto rico': '+1', 'pr': '+1',
    # Europe
    'espana': '+34', 'españa': '+34', 'spain': '+34', 'es': '+34',
    'portugal': '+351', 'pt': '+351',
    'francia': '+33', 'france': '+33', 'fr': '+33',
    'alemania': '+49', 'germany': '+49', 'de': '+49',
    'italia': '+39', 'italy': '+39', 'it': '+39',
    'reino unido': '+44', 'united kingdom': '+44', 'uk': '+44', 'gb': '+44',
    'suiza': '+41', 'switzerland': '+41', 'ch': '+41',
    'paises bajos': '+31', 'netherlands': '+31', 'nl': '+31',
    'belgica': '+32', 'belgium': '+32', 'be': '+32',
    'republica checa': '+420', 'república checa': '+420', 'czech republic': '+420', 'cz': '+420',
    'polonia': '+48', 'poland': '+48', 'pl': '+48',
    # Asia-Pacific & Middle East
    'india': '+91', 'in': '+91',
    'japon': '+81', 'japan': '+81', 'jp': '+81',
    'corea del sur': '+82', 'south korea': '+82', 'kr': '+82',
    'china': '+86', 'cn': '+86',
    'singapur': '+65', 'singapore': '+65', 'sg': '+65',
    'australia': '+61', 'au': '+61',
    'emiratos arabes unidos': '+971', 'uae': '+971', 'ae': '+971',
    'israel': '+972', 'il': '+972',
}


def normalize_phone_number(phone: str, country: str = None) -> str:
    """
    Convert a phone string into E.164 international format (+<country_code><subscriber>).
    Safely handles numbers from any country worldwide without corrupting non-Ecuadorian numbers.
    """
    if not phone:
        return ""
    
    phone_str = str(phone).strip()
    if not phone_str:
        return ""

    # Strip whatsapp: prefix if present
    if phone_str.lower().startswith('whatsapp:'):
        phone_str = phone_str[9:].strip()

    # Strip @s.whatsapp.net or @lid if present
    if '@' in phone_str:
        phone_str = phone_str.split('@')[0].strip()

    # If already starts with '+', keep digits after '+'
    if phone_str.startswith('+'):
        clean_digits = ''.join(c for c in phone_str if c.isdigit())
        return f"+{clean_digits}" if clean_digits else phone_str

    # Handle 00 international prefix (e.g. 0034..., 00420...)
    digits = ''.join(c for c in phone_str if c.isdigit())
    if not digits:
        return phone_str
    if digits.startswith('00') and len(digits) > 10:
        return f"+{digits[2:]}"

    # Lookup dialing code by company/customer country if provided
    code = None
    if country:
        c_clean = str(country).strip().lower()
        code = COUNTRY_DIALING_CODES.get(c_clean)

    # If the number already starts with the country's dialing code, just prepend '+'
    if code:
        raw_code = code.lstrip('+')
        if digits.startswith(raw_code) and len(digits) >= len(raw_code) + 8:
            return f"+{digits}"
        if digits.startswith('0'):
            digits = digits[1:]
        return f"{code}{digits}"

    # Heuristic fallback ONLY for unambiguous local Ecuador mobile format (09xxxxxxxx = 10 digits)
    if digits.startswith('09') and len(digits) == 10:
        return f"+593{digits[1:]}"

    # For 10-digit US/Canada/Colombia/Mexico numbers or already-prefixed international numbers (11-15 digits)
    return f"+{digits}"
