from pydantic import BaseModel, model_validator, Field
import uuid

class SendMessageModel(BaseModel):
    message: str
    channel_number: int = Field(ge=1, le=1000)

class CreateChannelModel(BaseModel):
    channel_number: int = Field(ge=1, le=1000)
    channel_title: str = Field(min_length=3, max_length=50)
    channel_description: str = Field(min_length=5, max_length=255)