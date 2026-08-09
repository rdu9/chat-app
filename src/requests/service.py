from src.db.models import User, Chat, Message, ChatUserLink, Request, RequestStatus
import json
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
import uuid
from src.db.redis import redis_client
from .schemas import MakeRequestModel
from src.auth.service import UserService
from src.errors import (
    UserNotFound,
    ChatNotFound,
    NotChatOwner,
    AlreadyChatMember,
    RequestNotFound,
    RequestAlreadyExists,
    RequestAlreadyHandled,
)

user_service = UserService()


class RequestsService:

    async def add_request(
        self, chat_number: int, user_uid: uuid.UUID, session: AsyncSession
    ):
        new_chat_uid = uuid.UUID(int=chat_number)

        chat = await session.get(Chat, new_chat_uid)
        if not chat:
            raise ChatNotFound()

        if chat.owner_uid == user_uid:
            raise AlreadyChatMember()

        if await session.get(ChatUserLink, (new_chat_uid, user_uid)):
            raise AlreadyChatMember()

        statement = select(Request).where(
            Request.chat_uid == new_chat_uid,
            Request.user_uid == user_uid,
        )
        result = await session.exec(statement)
        if result.first():
            raise RequestAlreadyExists()

        new_request = Request()
        new_request.chat_uid = new_chat_uid
        new_request.user_uid = user_uid

        session.add(new_request)
        await session.commit()
        await session.refresh(new_request)
        return new_request

    async def see_requests(
        self,
        channel_id: int,
        user_uid: uuid.UUID,
        session: AsyncSession,
    ):
        chat_uid = uuid.UUID(int=channel_id)

        chat = await session.get(Chat, chat_uid)
        if chat is None:
            raise ChatNotFound()

        if chat.owner_uid != user_uid:
            raise NotChatOwner()

        statement = (
            select(Request.uid, User.username, Request.created_at)
            .join(User, User.uid == Request.user_uid)
            .where(Request.chat_uid == chat_uid)
            .where(Request.status == RequestStatus.pending)
            .order_by(desc(Request.created_at))
        )
        result = await session.exec(statement)
        return [
            {
                "request_uid": str(uid),
                "username": username,
                "created_at": created_at,
            }
            for uid, username, created_at in result.all()
        ]

    async def accept_request(
        self, request_uid: uuid.UUID, owner_uid: uuid.UUID, session: AsyncSession
    ):
        request = await session.get(Request, request_uid)
        if not request:
            raise RequestNotFound()

        if request.status != RequestStatus.pending:
            raise RequestAlreadyHandled()

        chat = await session.get(Chat, request.chat_uid)
        if not chat:
            raise ChatNotFound()

        if chat.owner_uid != owner_uid:
            raise NotChatOwner()

        user = await session.get(User, request.user_uid)
        if not user:
            raise UserNotFound()

        chat.chat_users.append(user)
        request.status = RequestStatus.approved
        await session.commit()
        return request

    async def decline_request(
        self, request_uid: uuid.UUID, owner_uid: uuid.UUID, session: AsyncSession
    ):
        request = await session.get(Request, request_uid)
        if not request:
            raise RequestNotFound()

        if request.status != RequestStatus.pending:
            raise RequestAlreadyHandled()

        chat = await session.get(Chat, request.chat_uid)
        if not chat:
            raise ChatNotFound()

        if chat.owner_uid != owner_uid:
            raise NotChatOwner()

        user = await session.get(User, request.user_uid)
        if not user:
            raise UserNotFound()

        request.status = RequestStatus.rejected
        await session.commit()
        return request

    async def add_member_directly():
        pass