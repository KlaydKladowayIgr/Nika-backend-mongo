import asyncio
import functools
from typing import List


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def create_counter():
    i = 0

    if i > 1000:
        i = 0

    def func():
        nonlocal i
        i += 1
        return i

    return func


async def validate_dict(key: str | List[str], data: dict) -> bool:
    match len(data):
        case 0:
            return False
        case 1:
            if key in data:
                return True
            return False
        case _:
            if all(k in data for k in key):
                return True
            return False


