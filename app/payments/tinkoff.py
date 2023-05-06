from hashlib import sha256
from app.config import CONFIG


async def generate_params_list(parameters: list[dict]) -> list[dict]:
    parameters.append({"Password": CONFIG.tinkoff_password})
    return [d for d in parameters if not set(d.keys()).issubset(["Receipt", "Data", "Token"])]


async def sort_params_list(params: list[dict]) -> list[dict]:
    sorted_keys = sorted([key for d in params for key in d.keys()])
    result = params.copy()
    for i in range(len(sorted_keys)):
        result[sorted_keys.index(*params[i].keys())] = params[i]

    return result


async def generate_token(parameters: list[dict]):
    raw_token = "".join(
        [str(value) if not isinstance(value, bool) else str(value).lower() for d in parameters for value in d.values()]
    )
    return sha256(raw_token.encode("utf-8")).hexdigest()
