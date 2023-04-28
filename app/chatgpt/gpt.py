import openai

from app.auth.models.user import User
from app.chatgpt.context import Context
from app.config import CONFIG

openai.api_key = CONFIG.gpt_api_key


async def ask(message: str):
    completion = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo",
                                                     messages=message)
    return completion


async def ask_with_context(message: str, user: User):
    ctx = await Context.get_context(user)
    print(ctx.messages)
    completion = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=ctx.messages
    )
    return completion
