from typing import Any, Callable

from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse

class ChatException(Exception):
    pass


# auth
class InvalidToken(ChatException):
    pass


class AccessTokenRequired(ChatException):
    pass


class RefreshTokenRequired(ChatException):
    pass


class NotAuthenticated(ChatException):
    pass


class InvalidCredentials(ChatException):
    pass


class UserAlreadyExists(ChatException):
    pass


class UserNotFound(ChatException):
    pass


# channels

class InvalidChannelNumber(ChatException):
    pass


class ChatNotFound(ChatException):
    pass


class ChatAlreadyExists(ChatException):
    pass


class NotChatOwner(ChatException):
    pass


class NotChatMember(ChatException):
    pass


class AlreadyChatMember(ChatException):
    pass


# requests 

class RequestNotFound(ChatException):
    pass


class RequestAlreadyExists(ChatException):
    pass


class RequestAlreadyHandled(ChatException):
    pass


# messages

class MessageNotFound(ChatException):
    pass


class EmptyMessage(ChatException):
    pass


# ------------

def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], JSONResponse]:

    async def exception_handler(request: Request, exc: ChatException):
        return JSONResponse(content=initial_detail, status_code=status_code)

    return exception_handler


def register_all_errors(app: FastAPI):

    # auth

    app.add_exception_handler(
        InvalidCredentials,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Invalid email or password",
                "error_code": "invalid_credentials",
            },
        ),
    )

    app.add_exception_handler(
        NotAuthenticated,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "You need to log in first",
                "error_code": "not_authenticated",
            },
        ),
    )

    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Your session is invalid or has expired",
                "error_code": "invalid_token",
            },
        ),
    )

    app.add_exception_handler(
        AccessTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "An access token is required for this action",
                "error_code": "access_token_required",
            },
        ),
    )

    app.add_exception_handler(
        RefreshTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "A refresh token is required for this action",
                "error_code": "refresh_token_required",
            },
        ),
    )

    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_409_CONFLICT,
            initial_detail={
                "message": "An account with that email already exists",
                "error_code": "user_already_exists",
            },
        ),
    )

    app.add_exception_handler(
        UserNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "That user was not found",
                "error_code": "user_not_found",
            },
        ),
    )

    # channels

    app.add_exception_handler(
        InvalidChannelNumber,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "message": "Channel numbers run from 1 to 1000",
                "error_code": "invalid_channel_number",
            },
        ),
    )

    app.add_exception_handler(
        ChatNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "That channel does not exist",
                "error_code": "chat_not_found",
            },
        ),
    )

    app.add_exception_handler(
        ChatAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_409_CONFLICT,
            initial_detail={
                "message": "That channel number is already taken",
                "error_code": "chat_already_exists",
            },
        ),
    )

    app.add_exception_handler(
        NotChatOwner,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Only the channel owner can do that",
                "error_code": "not_chat_owner",
            },
        ),
    )

    app.add_exception_handler(
        NotChatMember,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "You are not a member of this channel",
                "error_code": "not_chat_member",
            },
        ),
    )

    app.add_exception_handler(
        AlreadyChatMember,
        create_exception_handler(
            status_code=status.HTTP_409_CONFLICT,
            initial_detail={
                "message": "You are already a member of this channel",
                "error_code": "already_chat_member",
            },
        ),
    )

    # join requests

    app.add_exception_handler(
        RequestNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "That request does not exist",
                "error_code": "request_not_found",
            },
        ),
    )

    app.add_exception_handler(
        RequestAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_409_CONFLICT,
            initial_detail={
                "message": "You already have a request pending for this channel",
                "error_code": "request_already_exists",
            },
        ),
    )

    app.add_exception_handler(
        RequestAlreadyHandled,
        create_exception_handler(
            status_code=status.HTTP_409_CONFLICT,
            initial_detail={
                "message": "That request has already been accepted or declined",
                "error_code": "request_already_handled",
            },
        ),
    )

    # messages

    app.add_exception_handler(
        MessageNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "That message does not exist",
                "error_code": "message_not_found",
            },
        ),
    )

    app.add_exception_handler(
        EmptyMessage,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "message": "A message cannot be empty",
                "error_code": "empty_message",
            },
        ),
    )

    # ---

    @app.exception_handler(500)
    async def internal_server_error(request, exc):
        return JSONResponse(
            content={
                "message": "Oops! Something went wrong",
                "error_code": "server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )