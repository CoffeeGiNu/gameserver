import json
import uuid
from enum import Enum, IntEnum
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine


class InvalidToken(Exception):
    """指定されたtokenが不正だったときに投げる"""


class SafeUser(BaseModel):
    """token を含まないUser"""

    id: int
    name: str
    leader_card_id: int

    class Config:
        orm_mode = True


def create_user(name: str, leader_card_id: int) -> str:
    """Create new user and returns their token"""
    token = str(uuid.uuid4())
    # NOTE: tokenが衝突したらリトライする必要がある.
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `user` (name, token, leader_card_id) VALUES (:name, :token, :leader_card_id)"
            ),
            {"name": name, "token": token, "leader_card_id": leader_card_id},
        )
        # print(result)
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    # TODO: 実装
    result = conn.execute(
        text("SELECT `id`, `name`, `leader_card_id` FROM `user` WHERE `token`=:token"),
        {"token": token},
    )
    try:
        row = result.one()
    except NoResultFound:
        return None
    return SafeUser.from_orm(row)


def get_user_by_token(token: str) -> Optional[SafeUser]:
    with engine.begin() as conn:
        return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
    # このコードを実装してもらう
    with engine.begin() as conn:
        # TODO: 実装
        result = conn.execute(
            text(
                "UPDATE `user` SET `name`=:name, `leader_card_id`=:leader_card_id WHERE `token`=:token"
            ),
            {"name": name, "token": token, "leader_card_id": leader_card_id},
        )
        # print(result)
    # return token


MAX_USER_COUNT = 4


class LiveDifficulty(Enum):
    normal = 1
    hard = 2


class JoinRoomResult(Enum):
    Ok = 1
    RoomFull = 2
    Disbanded = 3
    OtherError = 4


class WaitRoomStatus(Enum):
    Waiting = 1
    LiveStart = 2
    Dissolution = 3


class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count: int
    max_user_count: int = MAX_USER_COUNT

    class Config:
        orm_mode = True


class RoomUser(BaseModel):
    user_id: int
    name: str
    leader_card_id: int
    select_difficulty: LiveDifficulty
    is_me: bool
    is_host: bool

    class Config:
        orm_mode = True


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: list[int]
    score: int


def room_create(live_id: int, select_difficulty: LiveDifficulty) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text("INSERT INTO `room` (live_id) VALUES (:live_id)"),
            {"live_id": live_id, "select_difficulty": select_difficulty.value},
        )
        room_id = result.lastrowid
    return room_id


def room_list(live_id: int) -> Optional[RoomInfo]:
    with engine.begin() as conn:
        # live_idが0のときは全曲が対象
        if live_id == 0:
            result = conn.execute(
                text("SELECT * FROM `room`"),
            )
        else:
            result = conn.execute(
                text("SELECT * FROM `room` WHERE `live_id`=:live_id"),
                {"live_id": live_id},
            )
        results = result.fetchall()
    available_rooms = []
    for res in results:
        available_room = RoomInfo(
            room_id=res.room_id,
            live_id=res.live_id,
            joined_user_count=res.joined_user_count,
        )
        available_rooms.append(available_room)
    return available_rooms


def room_join(
    user: SafeUser, room_id: int, select_difficulty: LiveDifficulty
) -> JoinRoomResult:
    # apiの仕様表にはuserについての記載はないがuserの情報は必要そうなので追加
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT `joined_user_count` FROM `room` WHERE `room_id`=:room_id"),
            {"room_id": room_id},
        )
        try:
            result = result.one()
        except NoResultFound:
            return JoinRoomResult.Disbanded
        user_count = result.joined_user_count
        if user_count < MAX_USER_COUNT:
            result = conn.execute(
                text(
                    "UPDATE `room_member` SET `joined_user_count`=:now_user_count WHERE `room_id`=:room_id"
                ),
                dict(
                    room_id=room_id,
                    user_id=user.id,
                    now_user_count=user_count + 1,
                    select_difficulty=select_difficulty.value,
                ),
            )
            return JoinRoomResult.Ok
        elif user_count >= MAX_USER_COUNT:
            return JoinRoomResult.RoomFull
        elif user_count == 0:
            # 実際にこの状況がありえるのかわからないが一応用意しておく
            return JoinRoomResult.Disbanded
        else:
            return JoinRoomResult.OtherError


def room_wait(room_id: int):
    pass
