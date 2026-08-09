from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from .utils import decode_token
from .service import UserService
from src.db.redis import token_in_blocklist
import uuid
from src.errors import NotAuthenticated, InvalidToken

user_service = UserService()


async def current_user_uid(request: Request) -> uuid.UUID:
    token = request.cookies.get("access_token")
    if token is None:
        raise NotAuthenticated()

    payload = decode_token(token)
    if payload is None or payload.get("refresh"):
        raise InvalidToken()

    return uuid.UUID(payload["user"]["user_uid"])




# --------------

#class TokenBearer(HTTPBearer):
#
#    def __init__(self, auto_error=True):
#        super().__init__(auto_error=auto_error)
#
#    async def __call__(self, request: Request) -> dict | None:
#
#        creds = await super().__call__(request)
#
#        if creds is None:                 
#            return None
#
#        token = creds.credentials
#
#        token_data = decode_token(token)
#
#        if not token_data:                     
#            self._reject("Invalid or expired token")
#
#        if await token_in_blocklist(token_data["jti"]):
#            self._reject("Token has been revoked")
#
#        self.verify_token_data(token_data)  
#        return token_data
#
#    def _reject(self, detail: str):
#        if self.auto_error:
#            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail)
#        return None
#
#    def verify_token_data(self, token_data: dict) -> None:  
#        raise NotImplementedError("Override this in a child class")
#
#
#class AccessTokenBearer(TokenBearer):
#    def verify_token_data(self, token_data: dict) -> None:
#        if token_data.get("refresh"):          
#            raise HTTPException(
#                status.HTTP_401_UNAUTHORIZED, "Provide an access token"
#            )
#
#
#class RefreshTokenBearer(TokenBearer):
#    def verify_token_data(self, token_data: dict) -> None:
#        if not token_data.get("refresh"):
#           raise HTTPException(
#                status.HTTP_401_UNAUTHORIZED, "Provide a refresh token"
#            )