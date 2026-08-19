import re


def redact_sensitive_data(text: str):

    if not text:
        return text


    # Mask email IDs
    # Example:
    # james.mitchell@gmail.com -> j****@gmail.com
    text =  re.sub(
        r"\b([A-Za-z0-9])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b",
        r"\1****\2",
        text
    )


    # Mask Card IDs
    # Example:
    # CC-881001 -> CC-****001
    text = re.sub(
        r"\bCC-\d+\b",
        lambda match: "CC-****" + match.group()[-3:],
        text
    )

    return text