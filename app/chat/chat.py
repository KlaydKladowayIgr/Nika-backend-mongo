from app.auth.models.user import User
from app.chat.exceptions import MessageNotFound
from app.chat.models import Message, ChatMessage
from bson.objectid import ObjectId
from beanie import PydanticObjectId


async def get_all_messages(user: User) -> list[ChatMessage]:
    return await Message.find(Message.user.id == user.id).project(ChatMessage).to_list()


async def get_message(user: User, msg_id: PydanticObjectId) -> ChatMessage:
    query = await Message.find_one(Message.user.id == user.id, Message.id == msg_id).project(ChatMessage)
    return query


async def get_messages_count(user: User) -> int:
    return await Message.find(Message.user.id == user.id).count()


async def get_messages_selection(user: User, start: int = None, end: int = None) -> list[ChatMessage]:
    return await Message.find(Message.user.id == user.id, skip=start, limit=end).project(ChatMessage).to_list()


async def add_message(user: User, message: str, role: str = "user") -> PydanticObjectId:
    msg = Message(role=role, content=message, user=user)
    await msg.create()

    return msg.id


async def delete_message(user: User, msg_id: str) -> PydanticObjectId:
    msg = await Message.find_one(Message.user.id == user.id, Message.id == ObjectId(msg_id))

    if not msg:
        raise MessageNotFound

    await msg.delete()

    return msg.id
