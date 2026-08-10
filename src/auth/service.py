from src.db.models import User, Chat, Message, ChatUserLink
import json
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from .utils import generate_passwd_hash
import uuid
from src.db.redis import redis_client
from src.config import Config
from .schemas import UserCreateModel, UserLoginModel, UserPasswordResetModel
from src.errors import (
    UserAlreadyExists,
    UserNotFound,
    ChatNotFound,
    ChatAlreadyExists,
    NotChatOwner,
    NotChatMember,
    AlreadyChatMember,
)
from starlette.concurrency import run_in_threadpool


class UserService:

    async def create_user(self, payload: UserCreateModel, session: AsyncSession):
        user_email = payload.email
        if await self.user_exists(user_email, session):
            raise UserAlreadyExists()

        user_model_dict = payload.model_dump()
        new_user = User(**user_model_dict)

        hashed = await run_in_threadpool(generate_passwd_hash, payload.password)
        new_user.password_hash = hashed

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

    async def user_exists(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            return False
        return True

    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            return None
        return result_first

    async def get_username_by_uid(self, uid: uuid.UUID, session: AsyncSession):
        statement = select(User.username).where(User.uid == uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        return result_first

    async def add_user_to_chat(
        self,
        user_to_add_uid: uuid.UUID,
        user_uid: uuid.UUID,
        chat_number: int,
        session: AsyncSession,
    ):

        chat_uid = uuid.UUID(int=chat_number)

        chat = await session.get(Chat, chat_uid)
        if not chat:
            raise ChatNotFound()

        if chat.owner_uid != user_uid:
            raise NotChatOwner()

        user = await session.get(User, user_to_add_uid)
        if not user:
            raise UserNotFound()

        if await session.get(ChatUserLink, (chat_uid, user_to_add_uid)):
            raise AlreadyChatMember()

        chat.chat_users.append(user)
        await session.commit()

        return True

    async def save_messsage(
        self,
        message_content: str,
        user_uid: uuid.UUID,
        chat_uid: int,
        session: AsyncSession,
    ):

        new_message = Message()
        new_message.message_content = message_content
        new_message.user_uid = user_uid
        new_message.chat_uid = uuid.UUID(int=chat_uid)

        session.add(new_message)
        await session.commit()
        await session.refresh(new_message)
        return new_message

    async def create_chat(
        self,
        chat_title: str,
        chat_description: str,
        chat_uid: int,
        owner_uid: uuid.UUID,
        session: AsyncSession,
    ):

        new_chat_uid = uuid.UUID(int=chat_uid)

        if await session.get(Chat, new_chat_uid):
            raise ChatAlreadyExists()

        owner_object = await session.get(User, owner_uid)
        if not owner_object:
            raise UserNotFound()

        new_chat = Chat()
        new_chat.chat_title = chat_title
        new_chat.chat_description = chat_description
        new_chat.owner_uid = owner_uid
        new_chat.uid = new_chat_uid
        new_chat.chat_users.append(owner_object)

        session.add(new_chat)
        await session.commit()
        await session.refresh(new_chat)
        return new_chat

    async def get_chat_by_uid(self, chat_uid: int, session: AsyncSession):
        new_chat_uid = uuid.UUID(int=chat_uid)
        statement = select(Chat).where(Chat.uid == new_chat_uid)
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            return None
        return result_first

    async def post_message_logic(
        self, chat_uid: int, user_uid: uuid.UUID, text: str, session: AsyncSession
    ):
        new_chat_uid = uuid.UUID(int=chat_uid)

        chat = await session.get(Chat, new_chat_uid)
        if not chat:
            raise ChatNotFound()

        user = await session.get(User, user_uid)
        if not user:
            raise UserNotFound()

        link = await session.get(ChatUserLink, (new_chat_uid, user_uid))
        if not link:
            raise NotChatMember()

        new_message = Message()
        new_message.message_content = text
        new_message.user_uid = user_uid
        new_message.chat_uid = new_chat_uid

        session.add(new_message)
        await session.commit()
        await session.refresh(new_message)

        await redis_client.publish(
            f"channel:{chat_uid}",
            json.dumps(
                {"username": user.username, "channel_id": chat_uid, "message": text}
            ),
        )
        return new_message