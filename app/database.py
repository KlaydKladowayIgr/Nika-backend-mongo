from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import CONFIG

DATABASE_URI_WITH_AUTH = f"mongodb://{CONFIG.db_user}:{CONFIG.db_pass}@{CONFIG.db_host}:{CONFIG.db_port}"
DATABASE_URI = f"mongodb://{CONFIG.db_host}:{CONFIG.db_port}"


async def init_db(models: list):
    client = AsyncIOMotorClient(DATABASE_URI)
    await init_beanie(database=client.db_name, document_models=models)
