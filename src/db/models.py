from sqlmodel import SQLModel, Field, Column, Relationship
import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy import ForeignKey
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import UniqueConstraint
import enum


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ReactionType(str, enum.Enum):
    rolf = "rolf"
    joy = "joy"
    skull = "skull"
    heart = "heart"


class ChatUserLink(SQLModel, table=True):
    __tablename__ = "chat_user_link"

    chat_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("chats.uid", ondelete="CASCADE"), primary_key=True
        )
    )
    user_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True
        )
    )


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )
    username: str = Field(min_length=2, max_length=20, unique=True, nullable=False)
    password_hash: str = Field(exclude=True)
    email: str = Field(min_length=4)
    # TO ADD: is_verified
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )

    user_messages: List["Message"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    # ==================

    user_chats: List["Chat"] = Relationship(
        back_populates="chat_users",
        link_model=ChatUserLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )

    owner_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID, ForeignKey("users.uid", ondelete="SET NULL"), nullable=True
        ),
    )

    chat_title: str = Field(min_length=3, max_length=50)
    chat_description: Optional[str] = Field(default=None, min_length=5, max_length=255)

    chat_messages: List["Message"] = Relationship(
        back_populates="chat",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )

    # ==============

    chat_users: List["User"] = Relationship(
        back_populates="user_chats",
        link_model=ChatUserLink,
        sa_relationship_kwargs={
            "lazy": "selectin",
        },
    )


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    message_content: str = Field(min_length=1, max_length=2000)

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )

    sent_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )

    user_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=True
        ),
    )

    chat_uid: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID, ForeignKey("chats.uid", ondelete="CASCADE"), nullable=True
        ),
    )

    user: Optional["User"] = Relationship(back_populates="user_messages")
    chat: Optional["Chat"] = Relationship(back_populates="chat_messages")


class Request(SQLModel, table=True):
    __tablename__ = "requests"
    __table_args__ = (UniqueConstraint("chat_uid", "user_uid"),)

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )

    chat_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("chats.uid", ondelete="CASCADE"), nullable=False
        )
    )

    user_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
        )
    )

    status: RequestStatus = Field(default=RequestStatus.pending)
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )


class Reaction(SQLModel, table=True):
    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint("message_uid", "user_uid", "reaction_type"),
    )

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True),
    )

    message_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("messages.uid", ondelete="CASCADE"), nullable=False
        )
    )

    user_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
        )
    )

    reaction_type: ReactionType

    added_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(pg.TIMESTAMP)
    )