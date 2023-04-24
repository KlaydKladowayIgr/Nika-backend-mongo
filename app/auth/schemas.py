import re

from pydantic import BaseModel, validator

"""
class PhoneNumber(BaseModel):
    number: int

    @validator("number")
    async def check_number(cls, num):
        if len(num) > 11:
            raise ValueError("Number length over 11 digits")

        pattern = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'

        if not bool(re.match(pattern, num)):
            raise ValueError("Invalid phone number format")

        return num
"""
