import asyncio

import socketio

sio = socketio.AsyncClient()


async def main():
    await sio.connect("http://localhost:8000",
                      auth={
                          "token": "eyJhbasd12GciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwaG9uZSI6Ijg4MDA1NTUzNTM1IiwiZXhwIjoxNjgyODg5MDAzfQ.9hynAJgWGdqpEn-ttgaxS8eA5SQvQjxqESgwKf4En34"
                      }
                      )
    await sio.wait()

@sio.on("add_message")
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
    #await sio.emit("test", {"start": 1, "end": 1}, callback=callback)
    await sio.emit("auth", {"phone": "88005553535"}, callback=callback)
    await asyncio.sleep(2)
    await sio.emit("auth_confirm", {"code": input(">>> ")}, callback=callback)
    await sio.wait()

if __name__ == "__main__":
    asyncio.run(main())
