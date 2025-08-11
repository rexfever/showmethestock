import re


def is_code(s: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", s))


def normalize_code_or_name(s: str) -> str:
    """입력이 접두사 포함 코드(예: KRX:005930)면 6자리 코드로 정규화.
    그 외에는 원본을 반환.
    """
    if not s:
        return s
    m = re.fullmatch(r"[A-Z]+:(\d{6})", s.strip(), flags=re.IGNORECASE)
    if m:
        return m.group(1)
    return s.strip()

