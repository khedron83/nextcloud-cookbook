import re
from math import gcd

_UNICODE_FRACS = {
    '½': 0.5, '⅓': 1/3, '⅔': 2/3, '¼': 0.25, '¾': 0.75,
    '⅛': 0.125, '⅜': 0.375, '⅝': 0.625, '⅞': 0.875,
}

# Matches: "1 1/2", "1/2", "2.5", "2", "½", "1½"
_NUM_PAT = (
    r'(?:\d+\s+\d+/\d+'          # mixed: 1 1/2
    r'|\d+/\d+'                   # fraction: 1/2
    r'|\d+\.?\d*'                 # decimal/int: 2, 1.5
    r'|[½⅓⅔¼¾⅛⅜⅝⅞]'              # unicode fraction alone
    r'|\d+[½⅓⅔¼¾⅛⅜⅝⅞]'           # mixed with unicode: 1½
    r')'
)

# (regex_for_unit, ml_per_unit)
_VOLUME: list[tuple[str, float]] = [
    (r'fl\.?\s*oz\.?|fluid\s+ounces?', 29.574),
    (r'cups?',                          240.0),
    (r'tbsps?|tablespoons?',            15.0),
    (r'tsps?|teaspoons?',               5.0),
    (r'pints?|pts?(?!\w)',              473.176),
    (r'quarts?|qts?(?!\w)',             946.353),
    (r'gallons?|gals?(?!\w)',           3785.41),
]

# (regex_for_unit, g_per_unit)
_WEIGHT: list[tuple[str, float]] = [
    (r'lbs?\.?|pounds?',   453.592),
    (r'oz\.?|ounces?',     28.3495),
]


def _parse(s: str) -> float | None:
    s = s.strip()
    if s in _UNICODE_FRACS:
        return _UNICODE_FRACS[s]
    for uf, val in _UNICODE_FRACS.items():
        if s.endswith(uf):
            try:
                return float(s[:-len(uf)]) + val
            except ValueError:
                pass
    m = re.match(r'^(\d+)\s+(\d+)/(\d+)$', s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
    m = re.match(r'^(\d+)/(\d+)$', s)
    if m:
        return int(m.group(1)) / int(m.group(2))
    try:
        return float(s)
    except ValueError:
        return None


def _fmt_vol(ml: float) -> str:
    if ml >= 950:
        return f"{ml / 1000:g} L"
    if ml >= 10:
        return f"{round(ml / 5) * 5} ml"
    return f"{round(ml, 1):g} ml"


def _fmt_wt(g: float) -> str:
    if g >= 950:
        return f"{g / 1000:g} kg"
    if g >= 10:
        return f"{round(g / 5) * 5} g"
    return f"{round(g, 1):g} g"


def convert_ingredient(text: str) -> str:
    result = text
    for unit_pat, factor in _VOLUME:
        def _repl(m, f=factor):
            qty = _parse(m.group(1))
            return _fmt_vol(qty * f) if qty is not None else m.group(0)
        result = re.sub(rf'({_NUM_PAT})\s*({unit_pat})\b', _repl, result, flags=re.IGNORECASE)
    for unit_pat, factor in _WEIGHT:
        def _repl(m, f=factor):
            qty = _parse(m.group(1))
            return _fmt_wt(qty * f) if qty is not None else m.group(0)
        result = re.sub(rf'({_NUM_PAT})\s*({unit_pat})\b', _repl, result, flags=re.IGNORECASE)
    return result


def _fmt_scaled(value: float) -> str:
    """Format a scaled quantity as a fraction when possible, otherwise decimal."""
    if value <= 0:
        return "0"
    for den in (2, 3, 4, 8):
        num = round(value * den)
        if abs(num / den - value) < 0.04:
            g = gcd(int(num), int(den))
            n, d = num // g, den // g
            if d == 1:
                return str(n)
            whole = n // d
            rem = n % d
            return f"{whole} {rem}/{d}" if whole else f"{rem}/{d}"
    if value >= 10:
        return f"{value:.0f}"
    s = f"{value:.2f}".rstrip('0').rstrip('.')
    return s


def scale_ingredient(text: str, factor: float) -> str:
    """Scale the leading quantity in an ingredient string by factor."""
    if abs(factor - 1.0) < 0.001:
        return text
    m = re.match(rf'^(\s*)({_NUM_PAT})(.*)', text, re.DOTALL)
    if not m:
        return text
    qty = _parse(m.group(2))
    if qty is None:
        return text
    return m.group(1) + _fmt_scaled(qty * factor) + m.group(3)


def convert_instruction(text: str) -> str:
    """Replace °F temperatures with °C equivalents."""
    def _f2c(m):
        c = round((float(m.group(1)) - 32) * 5 / 9 / 5) * 5
        return f"{c}°C"
    return re.sub(r'(\d+)\s*°?\s*F\b', _f2c, text, flags=re.IGNORECASE)
