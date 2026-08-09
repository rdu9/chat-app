from fastapi import APIRouter, status, WebSocket, Depends, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from src.db.redis import redis_client
import json
from src.auth.dependencies import current_user_uid
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session, async_session
import uuid
import asyncio
from .service import RequestsService
from src.auth.utils import decode_token
from .schemas import MakeRequestModel, AddUserModel
from src.chat.service import ChatService
from src.auth.service import UserService
from src.errors import ChatNotFound

request_router = APIRouter()
request_service = RequestsService()
chat_service = ChatService()
user_service = UserService()


# post requests
@request_router.post("", status_code=status.HTTP_200_OK)
async def make_a_request(
    payload: MakeRequestModel,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):

    chat_number = payload.chat_uid

    response = await chat_service.get_chat_by_uid(chat_number, session)
    if not response:
        raise ChatNotFound()

    response = await request_service.add_request(chat_number, user_uid, session)

    return response


# see requests
@request_router.get("/{channel_id}", status_code=status.HTTP_200_OK)
async def see_requests(
    channel_id: int,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    response = await request_service.see_requests(channel_id, user_uid, session)
    return response


# accept request
@request_router.post("/accept/{request_uid}", status_code=status.HTTP_200_OK)
async def accept_request(
    request_uid: uuid.UUID,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    response = await request_service.accept_request(request_uid, user_uid, session)
    return response


# decline request
@request_router.post("/decline/{request_uid}", status_code=status.HTTP_200_OK)
async def decline_request(
    request_uid: uuid.UUID,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    response = await request_service.decline_request(request_uid, user_uid, session)
    return response


# add someone directly
@request_router.post("/add", status_code=status.HTTP_200_OK)
async def add_member_to_chat(
    payload: AddUserModel,
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    user_uid_to_add = payload.user_to_add_uid
    chat_number = payload.chat_uid

    response = await user_service.add_user_to_chat(user_uid_to_add,user_uid,chat_number,session)
    return response