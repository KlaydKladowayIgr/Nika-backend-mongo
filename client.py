import asyncio

import socketio

sio = socketio.AsyncClient()


async def main():
    await sio.connect("http://localhost:8000",
                      auth={
                          "token": "token"
                      }
                      )
    await sio.wait()


@sio.on("set_phone")
async def phone(data):
    print(data)


@sio.on("send_sms")
async def message(data):
    print(data)


@sio.on("set_name")
async def set_name(data):
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
    await sio.emit("auth", {"phone": "phone"}, callback=callback)
    await asyncio.sleep(2)
    await sio.emit("auth_confirm", {"code": input(">>> ")}, callback=callback)

if __name__ == "__main__":
    asyncio.run(main())
