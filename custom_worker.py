from uvicorn.workers import UvicornWorker


class MyUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {"loop": "asyncio"}