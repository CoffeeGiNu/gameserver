from enum import Enum

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import (
    JoinRoomResult,
    LiveDifficulty,
    ResultUser,
    RoomInfo,
    RoomUser,
    SafeUser,
    WaitRoomStatus,
)

app = FastAPI()

# Sample APIs


@app.get("/")
async def root():
    return {"message": "Hello World"}


# User APIs


class UserCreateRequest(BaseModel):
    user_name: str
    leader_card_id: int


class UserCreateResponse(BaseModel):
    user_token: str


@app.post("/user/create", response_model=UserCreateResponse)
def user_create(req: UserCreateRequest):
    """新規ユーザー作成"""
    token = model.create_user(req.user_name, req.leader_card_id)
    return UserCreateResponse(user_token=token)


bearer = HTTPBearer()


def get_auth_token(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    assert cred is not None
    if not cred.credentials:
        raise HTTPException(status_code=401, detail="invalid credential")
    return cred.credentials


@app.get("/user/me", response_model=SafeUser)
def user_me(token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=404)
    # print(f"user_me({token=}, {user=})")
    return user


class Empty(BaseModel):
    pass
    
    class Config:
        orm_mode = True


@app.post("/user/update", response_model=Empty)
def user_update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    # print(req)
    model.update_user(token, req.user_name, req.leader_card_id)
    return Empty()


# Room APIs


class RoomCreateRequest(BaseModel):
    live_id: int
    select_difficulty: LiveDifficulty


class RoomCreateResponse(BaseModel):
    room_id: int


@app.post("/room/create", response_model=RoomCreateResponse)
def room_create(req: RoomCreateRequest, token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    room_id = model.room_create(user, req.live_id, req.select_difficulty)
    if room_id is None:
        raise HTTPException(status_code=404)
    # print(f"user_me({token=}, {user=})")
    return RoomCreateResponse(room_id=room_id)


class RoomListRequest(BaseModel):
    live_id: int


class RoomListResponse(BaseModel):
    room_info_list: list[RoomInfo]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(req: RoomListRequest):
    available_rooms = model.room_list(req.live_id)
    if available_rooms is None:
        raise HTTPException(status_code=404)
    return RoomListResponse(room_info_list=available_rooms)


class RoomJoinRequest(BaseModel):
    room_id: int
    select_difficulty: LiveDifficulty


class RoomJoinResponse(BaseModel):
    join_room_result: JoinRoomResult


@app.post("/room/join", response_model=RoomJoinResponse)
def room_join(req: RoomJoinRequest, token: str = Depends(get_auth_token)):
    user_id = model.get_user_by_token(token).id
    join_room_result = model.room_join(req.room_id, req.select_difficulty, user_id)
    return RoomJoinResponse(join_room_result=join_room_result)


class RoomWaitRequest(BaseModel):
    room_id: int


class RoomWaitResponse(BaseModel):
    status: WaitRoomStatus
    room_member: list[RoomUser]


# とりあえず雛形用意
@app.post("/room/wait", response_model=RoomWaitResponse)
def room_wait(req: RoomWaitRequest, token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    status, room_member = model.get_status_and_members(req.room_id, user.id)
    return RoomWaitResponse(status=status, room_member=room_member)


class RoomLeaveRequest(BaseModel):
    room_id: int


@app.post("/room/leave", response_model=Empty)
def room_leave(req: RoomLeaveRequest, token: str = Depends(get_auth_token)) -> Empty:
    user = model.get_user_by_token(token)
    model.room_leave(req.room_id, user.id)
    return Empty()


class RoomStartRequest(BaseModel):
    room_id: int


@app.post("/room/start", response_model=Empty)
def room_start(req: RoomStartRequest, token: str = Depends(get_auth_token)) -> Empty:
    user = model.get_user_by_token(token)
    model.room_start(req.room_id, user.id)
    return Empty


class RoomEndRequest(BaseModel):
    room_id: int
    judge_count_list: list[int]
    score: int


@app.post("/room/end", response_model=Empty)
def room_end(req: RoomEndRequest, token: str = Depends(get_auth_token)) -> Empty:
    user = model.get_user_by_token(token)
    model.room_end(req.room_id, req.judge_count_list, req.score, user.id)
    return Empty


class RoomResultRequest(BaseModel):
    room_id: int


class RoomResultResponse(BaseModel):
    result_user_list: list[ResultUser]


@app.post("/room/result", response_model=RoomResultResponse)
def room_result(req: RoomStartRequest) -> RoomResultResponse:
    result_user_list = model.room_result(req.room_id)
    return RoomResultResponse(result_user_list=result_user_list)

