import asyncio

from app.auth.models.user import User
from app.chatgpt.schemas import Message
from app.utils import db_obj_to_dict


class Context:
    def __init__(self, user: User):
        self.user = user

    def _check_role(self, role) -> bool:
        if role not in ("user", "system", "assistant"):
            return False
        return True

    @property
    def messages(self):
        messages = asyncio.run(Message.find(Message.user.id == self.user.id).to_list())
        return asyncio.run(db_obj_to_dict(messages, "role", "content"))[::-1]

    @classmethod
    async def get_context(cls, user) -> "Context":
        return cls(user)

    def add_message(self, role: str, message: str):
        if not self._check_role(role):
            raise ValueError("Incorrect role!")
        asyncio.run(Message(
            role=role,
            message=message,
            user=self.user
        ).create())
