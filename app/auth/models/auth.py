from datetime import datetime

from pydantic import BaseModel


class AccessToken(BaseModel):
    access_token: str
    access_expire: datetime


class RefreshToken(BaseModel):
    refresh_token: str
    refresh_expire: datetime
