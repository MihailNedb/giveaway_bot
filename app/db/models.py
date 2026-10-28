"""Модели базы данных."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GiveawayStatus(str, enum.Enum):
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    giveaways: Mapped[list["Giveaway"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[GiveawayStatus] = mapped_column(
        Enum(GiveawayStatus), default=GiveawayStatus.ACTIVE, index=True
    )
    winner_count: Mapped[int] = mapped_column(Integer, default=1)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    channel: Mapped["Channel"] = relationship(back_populates="giveaways")
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="giveaway", cascade="all, delete-orphan"
    )
    winners: Mapped[list["Winner"]] = relationship(
        back_populates="giveaway", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("giveaway_id", "user_id", name="uq_giveaway_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    giveaway: Mapped["Giveaway"] = relationship(back_populates="participants")


class Winner(Base):
    __tablename__ = "winners"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chosen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    giveaway: Mapped["Giveaway"] = relationship(back_populates="winners")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
