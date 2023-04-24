import re

import requests

from app.config import CONFIG


class SMSBaseException(Exception):
    def __init__(self, error_code, value):
        self.value = value
        self.code = error_code

    def __str__(self):
        return f"Error code: {self.code}. Message: {self.value}"


class SMSResponse:
    def __init__(self, data):
        self.code = data["response"]["msg"]["err_code"]
        self.text = data["response"]["msg"]["text"]
        self.type = data["response"]["msg"]["type"]


def _check_message(message) -> bool:
    return True if len(message) <= 737 else False


def _check_phone(phone) -> bool:
    return True if len(str(phone)) <= 11 else False


class SMSApi:
    sms_server = "http://api.sms-prosto.ru"

    def __init__(self, sender_name: str = "Nika"):
        self.key = CONFIG.sms_api_key
        self.name = sender_name

    @classmethod
    async def validate_phone(cls, phone: str) -> bool:
        if not isinstance(phone, str):
            return False
        return \
                bool(re.match(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$',
                              phone)) \
                and len(phone) <= 11

    async def send(self, phone: str, message: str, priority: int = 1) -> SMSResponse:
        """
        Sends the specified message to the specified phone number.
        Priority:
        1 - verification code
        2 - single notification
        3 - notifications sent to a small number of people
        4 - mass mailing

        :param message:
        :param phone:
        :param priority:
        :return: None
        """
        if not _check_message(message) or not await self.validate_phone(phone):
            raise ValueError("Incorrect input. Check message or phone length")
        params = {
            "method": "push_msg",
            "format": "json",
            "key": self.key,
            "text": message,
            "phone": phone,
            "sender_name": self.name,
            "priority": priority
        }
        payload = requests.get(self.sms_server, params=params)
        raw = SMSResponse(data=payload.json())

        if int(raw.code) != 0:
            raise SMSBaseException(raw.code, raw.text)

        return raw
