from typing import Literal

import openai

import app.chat.chat as chat
import pymongo
from app.auth.models.user import User
from app.config import CONFIG

openai.api_key = CONFIG.gpt_api_key

gpt_define = {"role": "system", "content": "Ты Ника. Ты голосовой помощник. Ты женского пола. тебя создала компания NNAI. Общайся со мной как с другом. А меня зовут {0}"}


async def transform_prompt(prompt: str) -> dict[Literal["role"] | Literal["content"], str]:
    return {"role": "user", "content": prompt}


async def generate_options(user: User) -> dict[Literal["role"] | Literal["content"], str]:
    options = gpt_define.copy()
    options["content"] = options["content"].format(user.name)

    return options


async def ask(user: User, prompt: str) -> str:
    completion = await openai.ChatCompletion.acreate(
        model=CONFIG.gpt_model,
        messages=[await generate_options(user), await transform_prompt(prompt)]
    )

    return completion.choices[0].message.content


async def ask_with_context(user: User, prompt: str) -> str:
    last_user_msg = await chat.Message.find_one(chat.Message.user.id == user.id,
                                                chat.Message.role == "user",
                                                sort=[("_id", pymongo.DESCENDING)])
    last_bot_msg = await chat.Message.find_one(chat.Message.user.id == user.id,
                                               chat.Message.role == "assistant",
                                               sort=[("_id", pymongo.DESCENDING)])

    messages = [await generate_options(user)]

    if last_user_msg and last_bot_msg:
        messages.append(await transform_prompt(last_user_msg.content))
        messages.append({"role": "assistant", "content": last_bot_msg.content})

    messages.append(await transform_prompt(prompt))

    completion = await openai.ChatCompletion.acreate(
        model=CONFIG.gpt_model,
        messages=messages
    )

    messages.clear()

    return completion.choices[0].message.content
