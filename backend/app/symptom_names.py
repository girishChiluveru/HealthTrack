def normalize_symptom_name(name: str) -> str:
    """Trim the name and collapse every run of whitespace into a single space."""
    return " ".join(name.split())


def symptom_key(name: str) -> str:
    """Build the key that groups spellings differing only in case or spacing."""
    return normalize_symptom_name(name).lower()
