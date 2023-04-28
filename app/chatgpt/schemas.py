from beanie import Document, Link

from app.auth.models.user import User


class Message(Document):
    role: str
    content: str
    user: Link[User]
