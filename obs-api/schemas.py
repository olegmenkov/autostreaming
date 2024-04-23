from enum import Enum
from typing import List
from typing import Literal

from pydantic import BaseModel


class UserId(BaseModel):
    user_id: str


class AddGroup(BaseModel):
    group_id: str


class AddGroupMember(BaseModel):
    group_id: str
    user_id: str
    is_admin: bool


class DeleteGroupMember(BaseModel):
    group_id: str
    user_id: str


class UsersAddObs(BaseModel):
    user_id: str
    obs_name: str
    ip: str
    port: str
    password: str


class AddGroupObs(BaseModel):
    group_id: str
    admin_id: str
    obs_names: List[str]


class UsersEditObs(BaseModel):
    user_id: str
    obs_name: str
    field_to_change: str
    new_value: str


class EditGroupObs(BaseModel):
    group_id: str
    obs_name: str
    field_to_change: str
    new_value: str


class UserDelObs(BaseModel):
    user_id: str
    obs_name: str


class DeleteGroupObs(BaseModel):
    group_id: str
    obs_name: str


class CheckObs(BaseModel):
    user_id: str
    need_availability: bool


class CheckGroupObs(BaseModel):
    group_id: str


class CheckObsGroups(BaseModel):
    user_id: str
    obs_name: str


class StartStreamModel(BaseModel):
    user_id: str
    obs_name: str
    key: str
    youtube_server: str


class StopStreamModel(BaseModel):
    user_id: str
    obs_name: str


class StartRecordingModel(BaseModel):
    user_id: str
    obs_name: str


class StopRecordingModel(BaseModel):
    user_id: str
    obs_name: str


class UserPingStreamObs(BaseModel):
    user_id: str
    obs_name: str


class PlanStreamModel(BaseModel):
    user_id: str
    date1: str
    date2: str
    key: str
    obs_name: str


class GetScenesModel(BaseModel):
    user_id: str
    obs_name: str


class SetSceneModel(BaseModel):
    user_id: str
    obs_name: str
    scene_name: str


class GetScheduleModel(BaseModel):
    user_id: str
    obs_name: str


class CalendarData(BaseModel):
    ip: str
    port: str
    password: str
    stream_key: str
    youtube_server: str


class CalendarDataStop(BaseModel):
    ip: str
    port: str
    password: str
    youtube_server: str


class UserObs(BaseModel):
    user_id: str
    obs_name: str


class ClientState(BaseModel):
    name: str
    time: str
    state: bool


class IpChange(BaseModel):
    name: str
    old_ip: str
    port: int
    new_ip: str
