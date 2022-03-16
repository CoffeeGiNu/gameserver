import json
from re import A
import uuid
from enum import Enum
from typing import Optional
from unittest import result

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import null, text
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
    is_me: bool = False
    is_host: bool = False

    class Config:
        orm_mode = True


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: list[int]
    score: int


def room_create(user: SafeUser, live_id: int, select_difficulty: LiveDifficulty) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `room` (live_id, joined_user_count, host) VALUES (:live_id, :joined_user_count, :host)"
            ),
            dict(live_id=live_id, joined_user_count=1, host=user.id),
        )
        room_id = result.lastrowid
        result = conn.execute(
            text(
                "INSERT INTO `room_member` (room_id, user_id, select_difficulty, is_host) VALUES (:room_id, :user_id, :select_difficulty, :is_host)"
            ),
            dict(
                room_id=room_id,
                user_id=user.id,
                select_difficulty=select_difficulty.value,
                is_host=True,
            ),
        )
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
    room_id: int, select_difficulty: LiveDifficulty, user_id: int
) -> JoinRoomResult:
    # 仕様表にはuserについての記載はないがuserの情報は必要そうなのでarg追加
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM `room` WHERE `room_id`=:room_id FOR UPDATE"),
            {"room_id": room_id},
        )
        result = result.one()
        if result is None:
            conn.execute(text("COMMIT"))
            return JoinRoomResult.OtherError
        user_count = result.joined_user_count
        if user_count >= MAX_USER_COUNT:
            conn.execute(text("COMMIT"))
            return JoinRoomResult.RoomFull
        elif user_count == 0:
            # 実際にこの状況がありえるのかわからないが一応用意しておく
            return JoinRoomResult.Disbanded
        if result.status == 1:
            conn.execute(
                text(
                    "INSERT INTO `room_member` (room_id, user_id, select_difficulty) VALUES (:room_id, :user_id, :select_difficulty)"
                ),
                dict(
                    room_id=room_id,
                    user_id=user_id,
                    select_difficulty=select_difficulty.value,
                ),
            )
            conn.execute(
                text(
                    "UPDATE `room` SET joined_user_count=:joined_user_count WHERE `room_id`=:room_id"
                ),
                dict(
                    joined_user_count=user_count + 1,
                    room_id=room_id,
                ),
            )
            conn.execute(text("COMMIT"))
            return JoinRoomResult.Ok
        else:
            return JoinRoomResult.Disbanded


def get_status_and_members(room_id: int, user_id: int):
    # TODO: 後で体裁を整える
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM `room_member` WHERE `room_id` = :room_id"),
            dict(room_id=room_id),
        )
        room_member = []
        rows = result.fetchall()

        result = conn.execute(
            text("SELECT * FROM `room` WHERE `room_id` = :room_id"),
            dict(room_id=room_id),
        )
        row = result.one()
        host = row.host
        status = row.status
        for row in rows:
            is_me = 0
            is_host = 0
            if row.user_id == user_id:
                is_me = 1
            if row.user_id == host:
                is_host = 1
            users = conn.execute(
                text("SELECT * FROM `user` WHERE `id` = :user_id"),
                dict(user_id=row.user_id),
            )
            user = users.one()
            room_member.append(
                RoomUser(
                    user_id=row.user_id,
                    name=user.name,
                    leader_card_id=user.leader_card_id,
                    select_difficulty=LiveDifficulty(row.select_difficulty),
                    is_me=is_me,
                    is_host=is_host,
                )
            )
    return status, room_member


def room_leave(room_id: int, user_id: int) -> None:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "SELECT is_host from room_member WHERE user_id=:user_id AND room_id=:room_id"
            ),
            {"user_id": user_id, "room_id": room_id},
        )
        is_host = result.one()[0]
        result = conn.execute(
            text("DELETE from room_member WHERE user_id=:user_id AND room_id=:room_id"),
            {"user_id": user_id, "room_id": room_id},
        )
        result = conn.execute(
            text("SELECT count(user_id) from room_member WHERE room_id = :room_id"),
            {"room_id": room_id},
        )
        joined_user_count = result.one()[0]
        if joined_user_count == 0:
            result = conn.execute(
                text("DELETE from room WHERE room_id = :room_id"),
                {"joined_user_count": joined_user_count, "room_id": room_id},
            )
        else:
            result = conn.execute(
                text(
                    "UPDATE room\
                    SET joined_user_count = :joined_user_count \
                    WHERE room_id = :room_id"
                ),
                {"joined_user_count": joined_user_count, "room_id": room_id},
            )
            if is_host:
                result = conn.execute(
                    text("SELECT user_id from room_member WHERE room_id = :room_id"),
                    {"room_id": room_id},
                )
                next_host_user_id = result.all()[0][0]
                result = conn.execute(
                    text(
                        "UPDATE room_member\
                        SET is_host = 1 \
                        WHERE room_id = :room_id AND user_id = :user_id"
                    ),
                    {
                        "room_id": room_id,
                        "user_id": next_host_user_id,
                    },
                )
    return None


def _get_room_by_room_id(conn, room_id):
    result = conn.execute(
        text("SELECT * FROM `room` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    return result


def room_start(room_id: int, user_id: int) -> None:
    with engine.begin() as conn:
        result = _get_room_by_room_id(conn, room_id)
        row = result.one()
        host = row.host
        if host != user_id:
            return
        result = conn.execute(
            text("UPDATE `room` SET `status`=:status WHERE `room_id`=:room_id"),
            dict(status=2, room_id=room_id),
        )
    return None


def _set_score(conn, room_id, judge_count_list, score, user_id):
    conn.execute(
        text(
            "UPDATE `room_member` SET judge_perfect=:judge_perfect, judge_great=:judge_great, judge_good=:judge_good, judge_bad=:judge_bad, judge_miss=:judge_miss, score=:score WHERE `room_id`=:room_id AND `user_id`=:user_id"
        ),
        dict(
            judge_perfect=judge_count_list[0],
            judge_great=judge_count_list[1],
            judge_good=judge_count_list[2],
            judge_bad=judge_count_list[3],
            judge_miss=judge_count_list[4],
            score=score,
            room_id=room_id,
            user_id=user_id,
        ),
    )


def room_end(room_id, judge_count_list, score, user_id) -> None:
    with engine.begin() as conn:
        _set_score(conn, room_id, judge_count_list, score, user_id)
    return None


def room_result(room_id: int) -> list[ResultUser]:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "SELECT user_id, judge_perfect, judge_great, judge_good, judge_bad, judge_miss, score FROM `room_member` WHERE room_id=:room_id"
            ),
            dict(room_id=room_id),
        )
        result_all = result.all()
        result_user_list = []
        is_all_result = True
        for result in result_all:
            if null == result.score:
                is_all_result = False
                return []
            result_user_list.append(
                ResultUser(
                    user_id=result.user_id,
                    judge_count_list=[
                        result.judge_perfect,
                        result.judge_great,
                        result.judge_good,
                        result.judge_bad,
                        result.judge_miss,
                    ],
                    score=result.score,
                )
            )

        result = conn.execute(
            text("UPDATE `room` SET `status`=:status WHERE room_id=:room_id"),
            dict(status=3, room_id=room_id)
        )
        conn.execute(text("COMMIT"))
    if is_all_result:
        return result_user_list
    else:
        return []
