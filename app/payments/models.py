from beanie import Document, Link
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.auth.models.user import User


class Tariff(Document):
    sum: float
    name: str
    duration: timedelta = timedelta(days=30)


class Order(Document):
    user: Link[User]
    sum: int
    promocode: str = None
    tariff: Link[Tariff]

    @property
    def created(self):
        return self.id.generation_time


class OrderRead(BaseModel):
    id: str
    user_id: str
    sum: float
    date: datetime
    tariff: str
    status: str = "new"

