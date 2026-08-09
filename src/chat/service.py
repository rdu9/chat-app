from src.db.models import User, Chat, Message, ChatUserLink, Reaction
import json
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import ReactionType
from sqlmodel import select, delete
import uuid
from src.db.redis import redis_client
from src.errors import (
    UserNotFound,
    ChatNotFound,
    ChatAlreadyExists,
    NotChatMember,
    NotChatOwner,
    MessageNotFound,
)


class ChatService:
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
                {
                    "type": "message",
                    "message_uid": str(new_message.uid),
                    "username": user.username,
                    "channel_id": chat_uid,
                    "message": text,
                    "sent_at": new_message.sent_at.isoformat(),
                }
            ),
        )
        return new_message

    async def delete_chat(
        self, chat_number: int, user_uid: uuid.UUID, session: AsyncSession
    ):
        new_chat_uid = uuid.UUID(int=chat_number)

        chat = await session.get(Chat, new_chat_uid)
        if not chat:
            raise ChatNotFound()

        if chat.owner_uid != user_uid:
            raise NotChatOwner()

        await session.delete(chat)
        await session.commit()
        return True

    async def toggle_reaction(
        self,
        message_uid: uuid.UUID,
        reaction_type: ReactionType,
        user_uid: uuid.UUID,
        session: AsyncSession,
    ):

        message = await session.get(Message, message_uid)
        if not message:
            raise MessageNotFound()

        chat_uid = message.chat_uid

        chatuserlink = await session.get(ChatUserLink, (chat_uid, user_uid))
        if not chatuserlink:
            raise NotChatMember()

        check_reaction = select(Reaction).where(
            Reaction.message_uid == message_uid,
            Reaction.user_uid == user_uid,
            Reaction.reaction_type == reaction_type,
        )

        result = await session.exec(check_reaction)
        result_first = result.first()

        if result_first:
            await session.delete(result_first)
            action = "removed"
        else:
            new_reaction = Reaction()
            new_reaction.user_uid = user_uid
            new_reaction.message_uid = message_uid
            new_reaction.reaction_type = reaction_type
            session.add(new_reaction)
            action = "added"

        await session.commit()

        await redis_client.publish(
            f"channel:{chat_uid.int}",
            json.dumps(
                {
                    "type": "reaction",
                    "action": action,
                    "message_uid": str(message_uid),
                    "reaction_type": reaction_type.value,
                    "user_uid": str(user_uid),
                }
            ),
        )

        return {"action": action}
