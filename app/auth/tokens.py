from datetime import datetime, timedelta
from typing import Optional

import jwt

from app.auth.models.auth import TokensRead, Tokens
from app.auth.models.user import User
from app.config import CONFIG

key = CONFIG.auth_secret_key


async def validate_token(token: str, is_refresh=False) -> Optional[Tokens]:
    """
    Validates a token. Checks for the presence of a token in the database, lifetime

    :param token:
    :param is_refresh:
    :return:
    """
    try:
        jwt.decode(token, key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None

    if is_refresh:
        db_token = await Tokens.find_one(Tokens.refresh_token == token)
    else:
        db_token = await Tokens.find_one(Tokens.access_token == token)

    if not db_token:
        return None

    return db_token


async def authenticate(token: str) -> Optional[User]:
    db_token = await validate_token(token)
    if not db_token:
        return None

    user = await User.get(db_token.user.ref.id)
    return user


async def create_tokens(user: User) -> TokensRead:
    access_expire = datetime.utcnow() + timedelta(hours=48)
    refresh_expire = datetime.utcnow() + timedelta(days=30)

    return TokensRead(
        access_expire=access_expire,
        access_token=jwt.encode({"phone": user.phone, "exp": access_expire}, key),
        refresh_expire=refresh_expire,
        refresh_token=jwt.encode({"phone": user.phone, "exp": refresh_expire}, key)
    )


async def renew_tokens(token: str) -> bool:
    if not await validate_token(token, is_refresh=True):
        return False

    db_token = await Tokens.find_one(Tokens.refresh_token == token)

    user = await User.get(db_token.user.ref.id)
    await db_token.delete()

    tokens = await create_tokens(user)
    await Tokens(
        **tokens.dict(),
        user=user
    ).create()
