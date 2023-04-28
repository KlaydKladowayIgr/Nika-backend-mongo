import re


def check_phone(phone: str) -> str:
    if len(phone) >= 12:
        raise ValueError("The length of the phone number must be less than or equal to 11 characters")

    pattern = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
    if not bool(re.match(pattern, phone)):
        raise ValueError("Incorrect phone number format")

    return phone
