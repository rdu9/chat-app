from fastapi import APIRouter, status, Depends, Response
from fastapi.responses import JSONResponse
from .schemas import UserCreateModel, UserLoginModel, UserPasswordResetModel
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from .service import UserService
from .utils import create_token, verify_password
import uuid
from src.auth.dependencies import current_user_uid
from src.config import Config
from src.errors import InvalidCredentials

auth_router = APIRouter()
user_service = UserService()


@auth_router.post("/create")
async def create_user(
    payload: UserCreateModel, session: AsyncSession = Depends(get_session)
):
    user_email = payload.email

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

    access_token = create_token(user_data=user_data)
    refresh_token = create_token(user_data=user_data, refresh=True)

    response = JSONResponse(
        content={
            "message": "Account logged in successfully!",
            "user": user_data,
        },
        status_code=status.HTTP_200_OK,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=Config.COOKIE_SECURE,
        samesite="lax",
        max_age=15 * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=Config.COOKIE_SECURE,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth/refresh",
    )

    return response

@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token",path="/")
    response.delete_cookie("refresh_token",path="/api/v1/auth/refresh")
    return {"ok": True}

@auth_router.get("/me")
async def me(user_uid: uuid.UUID = Depends(current_user_uid)):
    return {"user_uid":str(user_uid)}





# ------------



#@auth_router.post("/login")
#async def login_user(
#    payload: UserLoginModel, session: AsyncSession = Depends(get_session)
#):
#    user_email = payload.email
#    check_user = await user_service.get_user_by_email(user_email, session)
#
#    if not check_user:
#       return None
#
#    user_password = payload.password
#    hashed_password = check_user.password_hash
#    valid = verify_password(user_password, hashed_password)
#
#    if not valid:
#        return None
#
#    user_uid = str(check_user.uid)
#
#   access_token = create_token(user_data={"email": user_email, "user_uid": user_uid})
#    refresh_token = create_token(user_data={"email": user_email, "user_uid": user_uid}, refresh=True)
#
#    if not access_token or not refresh_token:
#        return JSONResponse(
#            content={
#                "message": "Something went wrong during the creation of tokens"
#            },
#            status_code=status.HTTP_201_CREATED
#        )
#
#    return JSONResponse(
#        content={
#            "message": "Account logged in successfully!",
#            "access_token": access_token,
#            "refresh_token": refresh_token
#        },
#        status_code=status.HTTP_201_CREATED
#    )
