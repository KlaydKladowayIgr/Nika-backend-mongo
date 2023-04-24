from app.main import sio


@sio.on("test")
async def test(sid):
    return "Test"
