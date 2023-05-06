import asyncio
import threading
from typing import List, Any, Dict, Tuple

from beanie import Document


class RunThread(threading.Thread):
    def __init__(self, coro):
        self.coro = coro
        self.result = None
        super().__init__()

    def run(self):
        self.result = asyncio.run(self.coro)


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        thread = RunThread(coro)
        thread.start()
        thread.join()
        return thread.result
    else:
        return asyncio.run(coro)


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
            if isinstance(key, str): key = list(key)
            if all(k in data for k in key):
                return True
            return False


async def db_obj_to_dict(db_obj: Document | List[Document], *args) -> List[dict]:
    """
    Converts db_obj to the specified keys format

    :param db_obj:
    :return:
    """
    result = list()
    if hasattr(db_obj, "dict"):
        result.append(db_obj.dict())
        return result

    for j in db_obj:
        if hasattr(j, "dict"):
            raw_j = j.dict()
            result.append({key: value for key, value in raw_j.items() if key in args})

    return result


async def replace_dict_keys(d: dict, **kwargs) -> dict:
    res_d = d.copy()
    if not kwargs:
        raise ValueError("You must set keys!")

    for key, replace_key in kwargs.items():
        res_d[replace_key] = res_d.pop(key)

    return res_d
