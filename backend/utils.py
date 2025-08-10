import re


def is_code(s: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", s))


