from typing import Optional, NamedTuple, Tuple, Dict, Any

from app.auth.models.auth import Tokens, TokensRead
from app.auth.models.user import User
from app.auth.tokens import create_tokens
from app.auth.utils.sms import verify_code


class AuthData(NamedTuple):
    user: dict


async def authenticate(code: str) -> tuple[dict[str, User | TokensRead | Tokens | Any], bool] | None:
    db_code = await verify_code(code)

    if not db_code:
        return None

    user = await User.get_by_phone(db_code.phone)
    new_user = False
    if not user:
        user = User(
            phone=db_code.phone
        )
        await user.create()
        new_user = True

    tokens = await Tokens.find_one(Tokens.user.id == user.id)

    if tokens:
        tokens = TokensRead(**tokens.dict())

    if not tokens:
        tokens = await create_tokens(user)
        await Tokens(
            access_expire=tokens.access_expire,
            access_token=tokens.access_token,
            refresh_expire=tokens.refresh_expire,
            refresh_token=tokens.refresh_token,
            user=user
        ).create()

    return ({
        "user": user,
        "auth": tokens
    }, new_user)


async def logout(user: User):
    tokens = Tokens.find_one(Tokens.user.id == user.id)
    await tokens.delete()
