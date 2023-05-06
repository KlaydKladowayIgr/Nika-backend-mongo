from beanie import Document, Link
from pydantic import BaseModel, validator
from datetime import datetime

from app.auth.models.user import User


class MessageRead(BaseModel):
    role: str
    content: str


class Message(Document, MessageRead):
    user: Link[User]

    @property
    def created(self):
        return self.id.generation_time


class ChatMessage(BaseModel):
    id: str
    text: str
    type: str
    date: datetime

    class Settings:
        projection = {
            "id": "$_id",
            "type": "$role",
            "text": "$content",
            "date": "$_id.generation_time"
        }

    @validator("type")
    def setup_type(cls, t):
        if t != "user":
            return "bot"

        return t


    def __init__(self, **data):
        if data.get("_id"):
            if not data.get("date"):
                data["date"] = data["_id"].generation_time

            data["id"] = str(data["_id"])
        super().__init__(**data)
