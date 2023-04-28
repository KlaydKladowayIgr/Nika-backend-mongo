import asyncio

import socketio

sio = socketio.AsyncClient()


async def main():
    await sio.connect("http://localhost:8000",
                      auth={
                          "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwaG9uZSI6Ijg5OTk4NTg4NTQxIiwiZXhwIjoxNjgyNjc4OTIwfQ.PLfE_h2FjslLMp9x15n3h5ORR0MniYS2iShFgATM8Y8"}
                      )
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
async def connect(data=None):
    print(data)
    print("Connected")
    await sio.emit("auth", {"phone": "89998588541"}, callback=callback)
    await asyncio.sleep(2)
    code = input(">>> ")
    await sio.emit("auth_confirm", {"code": code}, callback=callback)


if __name__ == "__main__":
    asyncio.run(main())
