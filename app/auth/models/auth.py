from datetime import datetime

from beanie import Document, Link
from pydantic import BaseModel

from app.auth.models.user import User


class TokensRead(BaseModel):
    access_token: str
    access_expire: datetime

    refresh_token: str
    refresh_expire: datetime


class Tokens(Document, TokensRead):
    user: Link[User]
