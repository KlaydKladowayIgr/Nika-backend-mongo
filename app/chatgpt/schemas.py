from beanie import Document, Link

from app.auth.models.user import User


class Message(Document):
    role: str
    content: str
    user: Link[User]

    @property
    def created(self):
        return self.id.generation_time
