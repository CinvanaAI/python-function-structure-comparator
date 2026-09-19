def normalize_name(value: str, *, empty: str = "unknown") -> str:
    cleaned = value.strip().lower()
    return cleaned or empty
