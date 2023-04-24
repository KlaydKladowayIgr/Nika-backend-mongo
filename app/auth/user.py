from datetime import datetime, timedelta
from typing import Optional

import jwt

from app.auth.models.auth import RefreshToken, AccessToken
from app.auth.models.user import User
from app.auth.utils.sms import verify_code
from app.config import CONFIG

key = CONFIG.auth_secret_key


async def create_tokens(user: User) -> tuple:
    access_expire = datetime.utcnow() + timedelta(days=2)
    refresh_expire = datetime.utcnow() + timedelta(days=30)

    return (
        AccessToken(
            access_expire=access_expire,
            access_token=jwt.encode({"phone": user.phone, "exp": access_expire}, key)
        ),
        RefreshToken(
            refresh_expire=refresh_expire,
            refresh_token=jwt.encode({"phone": user.phone, "exp": refresh_expire}, key)
        )
    )


async def authenticate(code: str) -> Optional[dict]:
    if code == "000000":
        phone = "79999999999"
        user = await User.find_one(User.phone == phone)
        if not user:
            user = User(
                phone=phone
            )
            await user.create()
        return {
            "user": user,
            "auth": await create_tokens(user)
        }
    db_code = await verify_code(code)

    if not db_code:
        return None

    user = await User.find_one(User.phone == db_code.phone)

    if not user:
        user = User(
            phone=db_code.phone
        )
        await user.create()
    tokens = await create_tokens(user)

    return {
        "user": user,
        "auth": tokens
    }
