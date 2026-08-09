from fastapi import APIRouter, status, WebSocket, Depends, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from src.db.redis import redis_client
import json
from src.auth.dependencies import current_user_uid
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session, async_session
import uuid
import asyncio
from .service import ChatService
from src.auth.utils import decode_token
from .schemas import SendMessageModel, CreateChannelModel
from src.db.models import ReactionType
from sqlalchemy import func
from src.db.models import Reaction
from src.errors import (
    ChatException,
    InvalidChannelNumber,
    ChatAlreadyExists,
    ChatNotFound,
    NotChatMember,
    UserNotFound,
)

chat_router = APIRouter()
chat_service = ChatService()


@chat_router.post("/create", status_code=status.HTTP_200_OK)
async def create_channel(
    payload: CreateChannelModel,
    owner_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    chat_title = payload.channel_title
    chat_description = payload.channel_description
    chat_uid = payload.channel_number

    channel_check = await chat_service.get_chat_by_uid(chat_uid, session)
    if channel_check:
        raise ChatAlreadyExists()

    response = await chat_service.create_chat(
        chat_title, chat_description, chat_uid, owner_uid, session
    )
    return response


@chat_router.post("/message/{channel_id}", status_code=status.HTTP_200_OK)
async def send_a_message(
    payload: SendMessageModel,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    message = payload.message
    chat_uid = payload.channel_number

    response = await chat_service.post_message_logic(
        chat_uid=chat_uid, user_uid=user_uid, text=message, session=session
    )
    return response


@chat_router.delete("/{channel_id}", status_code=status.HTTP_200_OK)
async def delete_channel(
    channel_id: int,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    await chat_service.delete_chat(channel_id, user_uid, session)
    return {"message": "Channel deleted"}


@chat_router.post("/reaction/{message_uid}", status_code=status.HTTP_200_OK)
async def add_reaction(
    message_uid: uuid.UUID,
    reaction_type: ReactionType,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    response = await chat_service.toggle_reaction(
        message_uid, reaction_type, user_uid, session
    )
    return response


###


@chat_router.websocket("/{channel_id}")
async def chat_websocket(websocket: WebSocket, channel_id: int):
    await websocket.accept()

    user_uid = None
    token = websocket.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload and not payload.get("refresh"):
            user_uid = uuid.UUID(payload["user"]["user_uid"])

    if user_uid is None:
        await websocket.close(code=1008)
        return

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"channel:{channel_id}")

    async def redis_to_client():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_json(json.loads(message["data"]))

    forwarder = asyncio.create_task(redis_to_client())

    try:
        while True:
            data = await websocket.receive_json()

            if user_uid is None:
                await websocket.send_json(
                    {"error": "no token provided, login to send a message"}
                )
                continue

            async with async_session() as session:
                try:
                    await chat_service.post_message_logic(
                        channel_id, user_uid, data.get("message", ""), session
                    )
                except NotChatMember:
                    await websocket.send_json(
                        {"error": "you are not a member of this channel"}
                    )
                except ChatNotFound:
                    await websocket.send_json({"error": "that channel does not exist"})
                except ChatException:
                    await websocket.send_json({"error": "message could not be sent"})

    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        forwarder.cancel()
        await pubsub.unsubscribe(f"channel:{channel_id}")
        await pubsub.aclose()


# -----------------


from src.db.models import User, Chat, Message, ChatUserLink, Request, RequestStatus
import json
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import uuid
from src.db.redis import redis_client

PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>chat</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; }
    #log { border: 1px solid #ddd; padding: 12px; height: 400px; overflow-y: auto; }
    .msg { padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
    .who { font-weight: 600; margin-right: 6px; }
    .sys { color: #888; font-style: italic; border: none; }
  </style>
</head>
<body>
  <h2 id="title"></h2>
  <div id="log"></div>

<script>
const channel = location.pathname.split("/").pop();
document.getElementById("title").textContent = "Channel " + channel;

const proto = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(`${proto}//${location.host}/api/v1/chat/${channel}`);

function add(html, cls) {
  const log = document.getElementById("log");
  const div = document.createElement("div");
  div.className = cls || "msg";
  div.innerHTML = html;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

ws.onopen  = () => add("connected", "msg sys");
ws.onclose = () => add("disconnected", "msg sys");

ws.onmessage = (e) => {
  const d = JSON.parse(e.data);
  const who = (d.username || "anon").replace(/[<>&]/g, "");
  const txt = (d.message  || "").replace(/[<>&]/g, "");
  add(`<span class="who">${who}</span>${txt}`);
};
</script>
</body>
</html>
"""


@chat_router.get("/page/{channel_id}", response_class=HTMLResponse)
async def chat_page(channel_id: int):
    return PAGE


@chat_router.get("/mine")
async def my_chats(
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_uid)
    if not user:
        raise UserNotFound()

    member = [
        {
            "number": c.uid.int,
            "title": c.chat_title,
            "is_owner": c.owner_uid == user_uid,
        }
        for c in user.user_chats
    ]

    statement = (
        select(Request, Chat)
        .join(Chat, Request.chat_uid == Chat.uid)
        .where(Request.user_uid == user_uid, Request.status == RequestStatus.pending)
    )
    result = await session.exec(statement)
    pending = [{"number": c.uid.int, "title": c.chat_title} for _, c in result.all()]

    return {"member": member, "pending": pending}


@chat_router.get("/{channel_id}/messages")
async def chat_history(
    channel_id: int,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    statement = (
        select(Message, User)
        .join(User, Message.user_uid == User.uid)
        .where(Message.chat_uid == uuid.UUID(int=channel_id))
        .order_by(Message.sent_at.desc())
        .limit(50)
    )
    result = await session.exec(statement)
    rows = list(reversed(result.all()))

    message_uids = [m.uid for m, _ in rows]

    counts = {}
    mine = {}

    if message_uids:
        count_statement = (
            select(Reaction.message_uid, Reaction.reaction_type, func.count())
            .where(Reaction.message_uid.in_(message_uids))
            .group_by(Reaction.message_uid, Reaction.reaction_type)
        )
        count_result = await session.exec(count_statement)
        for msg_uid, reaction_type, total in count_result.all():
            counts.setdefault(msg_uid, {})[reaction_type.value] = total

        mine_statement = select(Reaction.message_uid, Reaction.reaction_type).where(
            Reaction.message_uid.in_(message_uids),
            Reaction.user_uid == user_uid,
        )
        mine_result = await session.exec(mine_statement)
        for msg_uid, reaction_type in mine_result.all():
            mine.setdefault(msg_uid, []).append(reaction_type.value)

    return [
        {
            "message_uid": str(m.uid),
            "username": u.username,
            "message": m.message_content,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "reactions": counts.get(m.uid, {}),
            "my_reactions": mine.get(m.uid, []),
        }
        for m, u in rows
    ]
