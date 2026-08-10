from fastapi import APIRouter, status, Depends, Response, Request
from fastapi.responses import JSONResponse
from .schemas import UserCreateModel, UserLoginModel, UserPasswordResetModel
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from src.db.models import User
from .service import UserService
from .utils import create_token, verify_password, decode_token
import uuid
from src.auth.dependencies import current_user_uid
from src.config import Config
from src.errors import InvalidCredentials, NotAuthenticated, InvalidToken, UserNotFound

auth_router = APIRouter()
user_service = UserService()


def set_access_cookie(response: JSONResponse, user_data: dict) -> None:
    response.set_cookie(
        key="access_token",
        value=create_token(user_data=user_data),
        httponly=True,
        secure=Config.COOKIE_SECURE,
        samesite="lax",
        max_age=15 * 60,
        path="/",
    )


def set_refresh_cookie(response: JSONResponse, user_data: dict) -> None:
    response.set_cookie(
        key="refresh_token",
        value=create_token(user_data=user_data, refresh=True),
        httponly=True,
        secure=Config.COOKIE_SECURE,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth/refresh",
    )


@auth_router.post("/create")
async def create_user(
    payload: UserCreateModel, session: AsyncSession = Depends(get_session)
):
    response = await user_service.create_user(payload, session)
    return response


@auth_router.post("/login")
async def login_user(
    payload: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    user_email = payload.email
    check_user = await user_service.get_user_by_email(user_email, session)

    if not check_user:
        raise InvalidCredentials()

    user_password = payload.password
    hashed_password = check_user.password_hash
    valid = verify_password(user_password, hashed_password)

    if not valid:
        raise InvalidCredentials()

    user_uid = str(check_user.uid)
    user_data = {"email": user_email, "user_uid": user_uid}

    response = JSONResponse(
        content={
            "message": "Account logged in successfully!",
            "user": user_data,
        },
        status_code=status.HTTP_200_OK,
    )

    set_access_cookie(response, user_data)
    set_refresh_cookie(response, user_data)

    return response


@auth_router.post("/refresh")
async def refresh_access_token(request: Request):
    """
    Swap a valid refresh token for a new access token.

    The browser only sends the refresh cookie to this path, because of the
    path= it was set with. This endpoint is the mirror image of
    current_user_uid: that one REJECTS refresh tokens, this one REQUIRES one.
    """
    token = request.cookies.get("refresh_token")
    if token is None:
        raise NotAuthenticated()

    payload = decode_token(token)
    if payload is None or not payload.get("refresh"):
        raise InvalidToken()

    user_data = payload["user"]

    response = JSONResponse(
        content={"message": "Token refreshed", "user": user_data},
        status_code=status.HTTP_200_OK,
    )
    set_access_cookie(response, user_data)

    return response


@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    return {"message": "Logged out"}


@auth_router.get("/me")
async def me(
    user_uid: uuid.UUID = Depends(current_user_uid),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_uid)
    if not user:
        raise UserNotFound()

    return {
        "user_uid": str(user.uid),
        "username": user.username,
        "email": user.email,
    }