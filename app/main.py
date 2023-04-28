import asyncio
import nest_asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi_sio import FastAPISIO

import app.auth.tokens as token_auth
import app.auth.user as user_auth
import app.auth.utils.sms as sms
import app.database as db

from app.auth.models.auth import Tokens
from app.auth.models.limits import Limit
from app.auth.models.user import *
from app.auth.sms_api import SMSBaseException
from app.chatgpt.schemas import Message
from app.schemas import WSResponse

app = FastAPI()
sio = FastAPISIO(app=app, mount_location='/')

chat_emitter = sio.create_emitter("add_message", WSResponse)


def authorized(func):
    def wrapper(sid, *args, **kwargs):
        session = asyncio.run(sio.get_session(sid))

        if not session:
            return jsonable_encoder(
                WSResponse(
                    status=404,
                    type="error",
                    data={"details": "Session not found"}
                )
            )

        if not session.get("token"):
            return jsonable_encoder(
                WSResponse(
                    status=401,
                    type="error",
                    data={"details": "Unauthorized"}
                )
            )

        if not asyncio.run(token_auth.validate_token(session["token"])):
            return jsonable_encoder(
                WSResponse(
                    status=401,
                    type="error",
                    data={"details": "Invalid token!"}
                )
            )

        return asyncio.run(func(sid, *args, **kwargs))

    return wrapper


@sio.on("connect")
async def on_connect(sid, data: dict, auth: dict):
    print(f"Session: {sid} connected")

    if not auth.get("token"):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect auth! "
                                 "If you are logging in for the first time, log in using the auth method"}
            )
        )

    user = await token_auth.authenticate(auth["token"])

    if not user:
        return jsonable_encoder(
            WSResponse(
                status=403,
                type="error",
                data={"details": "Invalid token!"}
            )
        )

    sio.enter_room(sid, room=user.id)
    await sio.save_session(sid,
                           {"token": auth["token"], "phone": user.phone, "can_send": False}
                           )

    return jsonable_encoder(
        WSResponse(
            status=201,
            type="info",
            data=user
        )
    )


@sio.on("disconnect")
async def on_disconnect(sid):
    pass


@sio.on("auth")
async def sms_auth(sid, data=None) -> dict:
    session: dict = await sio.get_session(sid) or data

    if not session:
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect data"}
            )
        )

    if not session.get("can_send", True):
        return jsonable_encoder(
            WSResponse(
                status=403,
                type="error",
                data={"details": "You cannot resend the code using this function. Use auth_retry!"}
            )
        )

    try:
        code = await sms.send_code(session["phone"])
        if not code:
            return jsonable_encoder(
                WSResponse(
                    status=403,
                    type="error",
                    data={"details": "You cannot resend the code using this function. Use auth_retry!"}
                )
            )

        if not isinstance(code, UserAuthCodeInfo):
            return jsonable_encoder(
                WSResponse(
                    status=500,
                    type="error",
                    data={"details": code.__str__()}
                )
            )

    except SMSBaseException as e:
        return jsonable_encoder(
            WSResponse(
                status=503,
                type="error",
                data={"details": f"SMS Service Error. {e.__str__()}"}
            )
        )

    await sio.save_session(sid, {"phone": session["phone"], "can_send": False})
    await Limit(
        phone=session["phone"]
    ).create()

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="auth",
            data=code
        )
    )


@sio.on("auth_retry")
async def sms_auth_retry(sid, *args, **kwargs) -> dict:
    session: dict = await sio.get_session(sid)

    if not session:
        return jsonable_encoder(
            WSResponse(
                status=404,
                type="error",
                data={"details": "Session not found"}
            )
        )

    if session.get("can_send"):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "You cannot resend the code without sending it earlier"}
            )
        )

    if not await sms.can_send_code(session["phone"]):
        return jsonable_encoder(
            WSResponse(
                status=403,
                type="error",
                data={"details": "It should take three minutes from the last time the code was sent to resend it"}
            )
        )

    phone_limit = await Limit.find_one(Limit.phone == session["phone"])

    if phone_limit.limit == 0:
        return jsonable_encoder(
            WSResponse(
                status=403,
                type="error",
                data={
                    "details": "SMS limit expired",
                    "expire": phone_limit.expire
                }
            )
        )

    try:
        code = await sms.send_code(session["phone"])
    except SMSBaseException as e:
        return jsonable_encoder(
            WSResponse(
                status=503,
                type="error",
                data={"details": f"SMS Service Error. {e.__str__()}"}
            )
        )

    phone_limit.limit -= 1
    await phone_limit.update()

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="auth",
            data=code
        )
    )


@sio.on("auth_cancel")
async def clean_phone(sid, *args, **kwargs) -> dict:
    session: dict = await sio.get_session(sid)

    if not session:
        return jsonable_encoder(
            WSResponse(
                status=404,
                type="error",
                data={"details": "Session not found"}
            )
        )

    await sio.save_session(sid, {"token": session["token"]} if session.get("token") else {})
    return jsonable_encoder(
        WSResponse(
            status=200,
            type="auth",
            data={"details": "Phone cleaned"}
        )
    )


@sio.on("auth_confirm")
async def auth(sid, data, *args, **kwargs):
    session: dict = await sio.get_session(sid)

    if not session:
        return jsonable_encoder(
            WSResponse(
                status=404,
                type="error",
                data={"details": "Session not found"}
            )
        )

    if not data.get("code"):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect data"}
            )
        )

    auth_data = await user_auth.authenticate(data["code"])

    if not auth_data:
        return jsonable_encoder(
            WSResponse(
                status=403,
                type="error",
                data={"details": "Invalid auth code"}
            )
        )

    session["token"] = auth_data["auth"].access_token
    sio.enter_room(sid, room=auth_data["user"].id)
    await sio.save_session(sid, session)

    if not auth_data["user"].name:
        welcome_msg = Message(
            role="system",
            content="Привет! Я Ника, а тебя как зовут?",
            user=auth_data["user"]
        )
        await chat_emitter.emit(
            WSResponse(
                status=200,
                type="bot",
                data=welcome_msg
            )
        )
        await welcome_msg.create()

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="auth",
            data=auth_data
        )
    )


@sio.on("logout")
@authorized
async def logout(sid, *args, **kwargs):
    session: dict = await sio.get_session(sid)
    session.pop("token")
    await sio.save_session(sid, session)

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="info",
            data={"details": "Logouted"}
        )
    )

@sio.on("set_name")
@authorized
async def set_username(sid, name=None):
    if not name:
        return
    session = await sio.get_session(sid)

    user = await User.get_by_phone(session["phone"])
    user.name = name["name"]
    await user.save()

    emitter = sio.create_emitter("update_user", model=WSResponse)
    await emitter.emit(
        WSResponse(
            status=200,
            type="info",
            data=user
        ),
        room=user.id
    )


@app.on_event("startup")
async def startup():
    await db.init_db([UserAuthCode, User, Message, Tokens, Limit])
    nest_asyncio.apply()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sms.check_codes, trigger=IntervalTrigger(seconds=1))
    scheduler.add_job(sms.check_limit, trigger=IntervalTrigger(seconds=1))
    scheduler.start()
