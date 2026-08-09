from pydantic import BaseModel
import uuid

class MakeRequestModel(BaseModel):
    chat_uid: int

class AddUserModel(BaseModel):
    chat_uid: int
    user_to_add_uid: uuid.UUID