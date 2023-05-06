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
import app.chat.chat as chat
import app.utils as utils
import app.payments.promocode as promo
import app.payments.tinkoff as tinkoff

from app.ai.chatgpt import gpt
from app.payments.models import Tariff, Order, OrderRead
from app.auth.models.auth import Tokens
from app.auth.models.limits import Limit
from app.auth.models.user import *
from app.auth.sms_api import SMSBaseException
from app.chat.models import Message, ChatMessage
from app.config import CONFIG
from app.schemas import WSResponse

app = FastAPI(docs_url=None, redoc_url=None)
sio = FastAPISIO(app=app, mount_location='/')

connect_emitter = sio.create_emitter("auth", model=WSResponse)
add_message_emitter = sio.create_emitter("add_message", model=WSResponse)


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


# Connect & Disconnect
@sio.on("connect")
async def on_connect(sid, data: dict, auth: dict = None):
    print(f"Session: {sid} connected")

    if auth and not auth.get("token"):
        await connect_emitter.emit(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect auth! "
                                 "If you are logging in for the first time, log in using the auth method"}
            ),
            to=sid
        )
        return
    if auth:
        auth_data = await token_auth.authenticate(auth["token"])

        if not auth_data:
            await connect_emitter.emit(
                WSResponse(
                    status=403,
                    type="error",
                    data={"details": "Invalid token!"}
                ),
                to=sid
            )
            return

        sio.enter_room(sid, room=auth_data["user"].id)
        await sio.save_session(sid,
                               {"token": auth["token"], "phone": auth_data["user"].phone, "can_send": False}
                               )
        print(f"Session {sid} authenticated")
        await connect_emitter.emit(
            WSResponse(
                status=200,
                type="info",
                data=auth_data
            ),
            to=sid
        )


@sio.on("disconnect")
async def on_disconnect(sid):
    pass


# Auth
@sio.on("auth")
async def sms_auth(sid, data=None) -> dict:
    session: dict = await sio.get_session(sid)

    if not data or not await utils.validate_dict("phone", data):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect data"}
            )
        )

    if "token" in session:
        return jsonable_encoder(
            WSResponse(
                status=403,
                type="error",
                data={"details": "You are already logged in"}
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
        code = await sms.send_code(data["phone"])
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

    await sio.save_session(sid, {"phone": data["phone"], "can_send": False})
    await Limit(
        phone=data["phone"]
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

    session["token"] = auth_data[0]["auth"].access_token
    sio.enter_room(sid, room=auth_data[0]["user"].id)
    await sio.save_session(sid, session)

    print(auth_data[1])

    if auth_data[1]:
        welcome_msg = Message(
            role="assistant",
            content="Привет! Я Ника, а тебя как зовут?",
            user=auth_data[0]["user"]
        )
        await welcome_msg.create()

        await add_message_emitter.emit(
            WSResponse(
                status=200,
                type="bot",
                data=ChatMessage(
                    id=str(welcome_msg.id),
                    text=welcome_msg.content,
                    type=welcome_msg.role,
                    date=welcome_msg.created
                )
            ),
            room=auth_data[0]["user"].id
        )
        print("send welcome")

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="auth",
            data=auth_data[0]
        )
    )


@sio.on("logout")
@authorized
async def logout(sid, *args, **kwargs):
    await sio.save_session(sid, {})

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="info",
            data={"details": "Logouted"}
        )
    )


# User update
@sio.on("set_name")
@authorized
async def set_username(sid, name=None):
    if not name:
        return
    session = await sio.get_session(sid)

    user = await User.get_by_phone(session["phone"])

    user_has_name = True

    if not user.name:
        user_has_name = False

    user.name = name["name"]
    await user.save()

    if not user_has_name:
        msg_id = await chat.add_message(user, message=user.name, role="user")
        msg_id_2 = await chat.add_message(user, message=f"Привет, {user.name}! Я твой голосовой помощник",
                                          role="assistant")

        await add_message_emitter.emit(
            WSResponse(
                status=200,
                type="info",
                data=await chat.get_message(user, msg_id)
            ),
            room=user.id
        )

        await add_message_emitter.emit(
            WSResponse(
                status=200,
                type="info",
                data=await chat.get_message(user, msg_id_2)
            ),
            room=user.id
        )

    emitter = sio.create_emitter("update_user", model=WSResponse)
    await emitter.emit(
        WSResponse(
            status=200,
            type="info",
            data=user
        ),
        room=user.id
    )
    return jsonable_encoder(
        WSResponse(
            status=200,
            type="info"
        )
    )


# System info
@sio.on("app_get_version")
async def get_app_version(sid, *args, **kwargs):
    await jsonable_encoder(
        WSResponse(
            status=200,
            type="info",
            data={"version": CONFIG.app_version}
        )
    )


# Chat
@sio.on("get_messages")
@authorized
async def get_messages(sid, options: dict = None):
    if not options:
        options = dict()

    session = await sio.get_session(sid)

    user = await User.get_by_phone(session["phone"])

    messages = await chat.get_messages_selection(user, options.get("start"), options.get("end"))

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="info",
            data=messages
        )
    )


@sio.on("add_message")
@authorized
async def add_message(sid, message: dict = None):
    if not message or not message.get("text"):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect message!"}
            )
        )
    session = await sio.get_session(sid)

    user = await User.get_by_phone(session["phone"])
    msg = await chat.get_message(user, await chat.add_message(user, message["text"]))

    await add_message_emitter.emit(
        WSResponse(
            status=200,
            type="info",
            data=msg
        ),
        room=user.id
    )

    answer = await gpt.ask_with_context(user, message["text"])

    bot_msg_id = await chat.add_message(user, answer, role="assistant")

    msg = await chat.get_message(user, bot_msg_id)

    await add_message_emitter.emit(
        WSResponse(
            status=200,
            type="info",
            data=msg
        ),
        room=user.id
    )

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="info",
            data={"details": f"Added message"}
        )
    )


@sio.on("delete_message")
@authorized
async def delete_message(sid, message: dict = None):
    if not message or not message.get("id"):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect message!"}
            )
        )

    session = await sio.get_session(sid)

    user = await User.get_by_phone(session["phone"])

    try:
        msg_id = await chat.delete_message(user, message["id"])

        emitter = sio.create_emitter("delete_message", model=WSResponse)
        await emitter.emit(
            WSResponse(
                status=204,
                type="info",
                data={"id": msg_id}
            ),
            room=user.id
        )

        return jsonable_encoder(
            WSResponse(
                status=200,
                type="info",
                data={"details": f"Deleted message"}
            )
        )
    except chat.MessageNotFound:
        return jsonable_encoder(
            WSResponse(
                status=404,
                type="error",
                data={"details": "Message not found!"}
            )
        )


# ChatGPT
@sio.on("clear_context")
@authorized
async def clear_gpt_context(sid, *args, **kwargs):
    session = await sio.get_session(sid)

    user = await User.get_by_phone(session["phone"])

    user_msg = await chat.get_message(user, await chat.add_message(user, "Забудь"))
    msg = await chat.get_message(user, await chat.add_message(user, "Хорошо, я всё забыла", role="assistant"))

    await add_message_emitter.emit(
        WSResponse(
            status=200,
            type="info",
            data=user_msg
        ),
        room=user.id
    )

    await add_message_emitter.emit(
        WSResponse(
            status=200,
            type="info",
            data=msg
        ),
        room=user.id
    )


# Payments
@sio.on("get_promocode")
@authorized
async def get_promocode(sid, promocode: dict = None):
    if not promocode or not promocode.get("promocode"):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect promocode"}
            )
        )

    try:
        db_promocode = await promo.get_promocode(promocode["promocode"])
    except promo.PromocodeNotFound:
        return jsonable_encoder(
            WSResponse(
                status=404,
                type="error",
                data={"details": "Promocode not found"}
            )
        )
    except promo.UserSubscriptionInvalid:
        return jsonable_encoder(
            WSResponse(
                status=403,
                type="error",
                data={"details": "Invalid user subscription"}
            )
        )

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="payment",
            data=promo.PromocodeRead(value=db_promocode.value, name=db_promocode.user.name)
        )
    )


@sio.on("new_order")
@authorized
async def create_order(sid, order: dict = None):
    if not order or not order.get("tariff"):
        return jsonable_encoder(
            WSResponse(
                status=400,
                type="error",
                data={"details": "Incorrect order"}
            )
        )
    tariff = await Tariff.find_one(Tariff.name == order["tariff"])
    if not tariff:
        return jsonable_encoder(
            WSResponse(
                status=404,
                type="error",
                data={"details": "Tariff not found"}
            )
        )

    promocode = order.get("promocode")
    if promocode:
        try:
            promocode = await promo.get_promocode(order["promocode"])
        except promo.PromocodeNotFound:
            return jsonable_encoder(
                WSResponse(
                    status=404,
                    type="error",
                    data={"details": "Promocode not found"}
                )
            )
        except promo.UserSubscriptionInvalid:
            return jsonable_encoder(
                WSResponse(
                    status=403,
                    type="error",
                    data={"details": "Invalid user subscription"}
                )
            )

    session = await sio.get_session(sid)
    user = await User.get_by_phone(session["phone"])

    summa = int(tariff.sum - (tariff.sum / 100) * promocode.sale) if promocode else tariff.sum
    order = Order(user=user,
                  tariff=tariff,
                  promocode=promocode.value if promocode else None,
                  sum=summa)
    await order.create()

    return jsonable_encoder(
        WSResponse(
            status=200,
            type="payment",
            data=OrderRead(
                id=str(order.id),
                user_id=str(order.user.id),
                sum=order.sum,
                date=order.created,
                tariff=order.tariff.name
            )
        )
    )


@app.post("/orders")
async def tinkoff_notification(**data):
    if not data.get("Token") or not data.get("Status") == "CONFIRMED":
        return

    params = await tinkoff.sort_params_list(await tinkoff.generate_params_list(data))
    token = await tinkoff.generate_token(params)

    if token != data["Token"]:
        return

    order = await Order.get(data["OrderId"])

    if not order:
        return

    user = order.user
    user.tariff = order.tariff.name
    user.tariff_expiration = datetime.utcnow() + order.tariff.duration \
        if promo.check_user_sub(user, "free") \
        else user.tariff_expiration + order.tariff.duration
    await user.update()

    if order.promocode:
        promo_user = (await promo.get_promocode(order.promocode)).user
        promo_user.balance += 100
        await promo_user.update()


@app.on_event("startup")
async def startup():
    await db.init_db([UserAuthCode, User, Message, Tokens, Limit, Tariff, Order])
    nest_asyncio.apply()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sms.check_codes, trigger=IntervalTrigger(seconds=1))
    scheduler.add_job(sms.check_limit, trigger=IntervalTrigger(seconds=1))
    scheduler.start()
