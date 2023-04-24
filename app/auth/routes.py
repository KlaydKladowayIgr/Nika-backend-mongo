from app.main import sio


@sio.on("connect")
async def connect(sid, data):
    print(sid, data)
