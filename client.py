import socketio
import asyncio

sio = socketio.AsyncClient()


async def main():
    await sio.connect("http://localhost:8000")
    await sio.wait()


@sio.on("set_phone")
async def phone(data):
    print(data)


@sio.on("send_sms")
async def message(data):
    print(data)


@sio.on("auth")
async def auth(data):
    print(data)


@sio.on("disconnect")
async def dis():
    print("Disconnected")


def callback(data):
    print(data)


@sio.on("connect")
async def connect():
    print("Connected")
    await sio.emit("auth", {"phone": "88005553535"}, callback=callback)
    await asyncio.sleep(5)
    await sio.emit("auth_retry", callback=callback)
    code = input("Code: ")
    await asyncio.sleep(10)
    await sio.emit("auth_confirm", {"code": code}, callback=callback)
    await asyncio.sleep(5)
    await sio.emit("auth_cancel", callback=callback)
    # await sio.emit("auth", {"code": "232140"})


if __name__ == "__main__":
    asyncio.run(main())
