import datetime
from fastapi.responses import JSONResponse
from loguru import logger

# from cryptography.fernet import Fernet
from conductor import Conductor
# from database import RedisDatabase
from db_class import Database
from obs_functions import start_youtube_stream, set_stream_parameters, start_recording
from obs_functions import stop_youtube_stream, ping_stream, stream_time, ping_recording, \
    recording_time, stop_recording, ping_obs, get_scenes, set_scene
from schemas import UserId, CalendarData, CalendarDataStop
from schemas import UsersAddObs, UserDelObs, UsersEditObs, CheckObs, StartStreamModel, \
    StopStreamModel, StartRecordingModel, StopRecordingModel, UserPingStreamObs, PlanStreamModel, UserObs, \
    GetScenesModel, SetSceneModel, AddGroup, AddGroupMember, DeleteGroupMember, AddGroupObs, \
    EditGroupObs, DeleteGroupObs, CheckGroupObs, CheckObsGroups, ClientState, IpChange
from utils import config_obsclient_calendar, DB_CONFIG

from fastapi import FastAPI



db = Database(**DB_CONFIG)
# new_db = Database(**DB_CONFIG)
app = FastAPI()
conductor = Conductor(db)

# @app.get('/show_bd')
# async def show_bd(user_id: UserId):
#     return JSONResponse(content=db.show_bd())


# Define callback functions

@app.post('/register_user')
async def register_user(user_id: UserId):
    """
    Функция, которая создает пользователя в базе данных (юзер стори обязательно
    должна начинаться с этого)
    # {'user_id': '1234'}
    :param user_id:
    :return:
    """
    logger.info('Register user')
    await conductor.create_user_in_db(user_id.user_id)
    logger.info(f'Added user {user_id.user_id} to database')
    return JSONResponse(content={'user_id': user_id.user_id})


@app.post('/start_stream')
async def start_stream(request_body: StartStreamModel):
    """
    Функция запуска стрима (сама делает проверки и возвращает ошибку, если
    пользователя нет в базе данных т.е. не было register_user; также ошибка
    будет в случае, если obs с таким именем нет)
    # {"user_id": "123", "obs_name": "obs_0", "key": "1234"}
    :param request_body:
    :return:
    """
    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)

    # if not await ping_obs(ip, port, password):
    #     return JSONResponse(status_code=409,
    #                         content='Obs stand is unavailable')

    resp = await ping_stream(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    if not resp["data"]:
        return JSONResponse(status_code=409,
                            content={'response': "Stream not running"})

    resp = await set_stream_parameters(ip, port, password, request_body.key, request_body.youtube_server)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    resp = await start_youtube_stream(ip, port, password, request_body.key, request_body.youtube_server)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    # logger.info(f"Started stream on obs "
    #             f"{obsclient.url.split('ws://')[1].split(':')[0]} by user "
    #             f"{request_body.user_id}")
    return JSONResponse(content={'response': "started stream successfully"})


@app.post('/stop_stream')
async def stop_stream(request_body: StopStreamModel):
    """
    Функция для прекращения стрима на obs с данным именем
    (проверки по аналогии со старт_стрим)
    {"user_id": "123", "obs_name": "obs_0"}
    :param request_body:
    :return:
    """
    logger.info('Stopping stream')
    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)

    # if await ping_obs(ip, port, password):
    #     return JSONResponse(status_code=409,
    #                         content='Obs stand is unavailable')

    resp = await ping_stream(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    if not resp["data"]:
        return JSONResponse(status_code=409,
                            content={'response': "Stream not running"})

    resp = await stop_youtube_stream(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    logger.info(f'Stream stopped successfully by {request_body.user_id}')
    return JSONResponse(content={'response': "stopped successfully"})


@app.post('/start_recording')
async def start_recording_handler(request_body: StartRecordingModel):
    """
    Функция запуска записи (сама делает проверки и возвращает ошибку, если
    пользователя нет в базе данных т.е. не было register_user; также ошибка
    будет в случае, если obs с таким именем нет)
    # {"user_id": "123", "obs_name": "obs_0"}
    :param request_body:
    :return:
    """
    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)
    # if not await ping_obs(ip, port, password):
    #     return JSONResponse(status_code=409,
    #                         content='Obs stand is unavailable')
    resp = await ping_recording(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    if resp["data"]:
        return JSONResponse(status_code=409,
                            content='Obs stand with this ip currently in use')

    resp = await start_recording(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])
    # logger.info(f"Started recording on obs "
    #             f"{obsclient.url.split('ws://')[1].split(':')[0]} by user "
    #             f"{request_body.user_id}")
    return JSONResponse(content={'response': "started recording successfully"})


@app.post('/stop_recording')
async def stop_recording_handler(request_body: StopRecordingModel):
    """
    Функция остановки записи (сама делает проверки и возвращает ошибку, если
    пользователя нет в базе данных т.е. не было register_user; также ошибка
    будет в случае, если obs с таким именем нет)
    # {"user_id": "123", "obs_name": "obs_0"}
    :param request_body:
    :return:
    """
    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)

    # if not await ping_obs(ip, port, password):
    #     return JSONResponse(status_code=409,
    #                         content='Obs stand is unavailable')

    resp = await ping_recording(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    if not resp["data"]:
        return JSONResponse(status_code=409,
                            content='Obs stand with this ip currently in use')

    resp = await stop_recording(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    # logger.info(f"Started recording on obs "
    #             f"{ip, port, password.url.split('ws://')[1].split(':')[0]} by user "
    #             f"{request_body.user_id}")
    return JSONResponse(content={'response': "started recording successfully"})


@app.get('/ping_redis')
async def ping_redis():
    """
    Endpoint для проверки, работает ли база данных
    :return:
    """
    if await conductor.ping_db():
        return {'database': 'OK!'}
    return {'database': 'Not available'}


@app.get('/ping')
async def ping():
    """
    Endpoint для проверки, работает ли сервис.
    :return:
    """
    return {'server': 'OK!'}


@app.post('/add_obs')
async def add_obs(request_body: UsersAddObs):
    logger.info('Adding users obs stand')
    await conductor.add_users_obs(request_body.user_id, request_body.obs_name,
                                  request_body.ip, request_body.port, request_body.password)
    logger.info(f'Added obs with ip {request_body.ip} for {request_body.user_id} in database')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.post('/edit_obs')
async def edit_obs(request_body: UsersEditObs):
    logger.info('Editing users obs stand')
    await conductor.edit_users_obs(request_body.user_id, request_body.obs_name,
                                   request_body.field_to_change, request_body.new_value)
    logger.info(f'Changed {request_body.field_to_change} for obs {request_body.obs_name}')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.post('/edit_group_obs')
async def edit_group_obs(request_body: EditGroupObs):
    logger.info('Editing group obs stand')
    await conductor.edit_groups_obs(request_body.group_id, request_body.obs_name, request_body.field_to_change,
                                    request_body.new_value)
    logger.info(f'Changed {request_body.field_to_change} for obs {request_body.obs_name}')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.post('/raise_to_admin')
async def raise_to_admin(request_body: DeleteGroupMember):
    logger.info('Raising user to admins')
    await conductor.raise_to_admin(request_body.user_id, request_body.group_id)
    logger.info(f'Raised user {request_body.user_id} to admin in group {request_body.group_id}')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.post('/remove_from_admins')
async def remove_from_admin(request_body: DeleteGroupMember):
    logger.info('Removing user from admins')
    await conductor.remove_from_admins(request_body.user_id, request_body.group_id)
    logger.info(f'Removed user {request_body.user_id} from admins in group {request_body.group_id}')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.delete('/delete_obs')
async def delete_obs(request_body: UserDelObs):
    logger.info('Deleting users obs stand')
    await conductor.del_users_obs(request_body.user_id, request_body.obs_name)
    logger.info(f'Deleted obs with ip {request_body.obs_name} for user {request_body.user_id} in database')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.delete('/delete_group_obs')
async def delete_groups_obs(request_body: DeleteGroupObs):
    logger.info('Deleting obs stand')
    deleted_obs_ip = await conductor.del_groups_obs(request_body.group_id, request_body.obs_name)
    logger.info(f'Deleted obs with ip {deleted_obs_ip} for group {request_body.group_id} in database')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.get('/check_obs')
async def check_obs(request_body: CheckObs):
    added_obs = await conductor.get_users_obs(request_body.user_id)
    need_availability = request_body.need_availability
    resp = dict()  # словарь {'имя обс': {параметры}, 'имя обс-2': {параметры-2}, ...}
    for obs in added_obs:
        name = obs[0]
        ip = obs[1]
        port = obs[2]
        ip, port, password = await conductor.get_obs_info(request_body.user_id, name)
        if need_availability:  # для доступных ОБС также смотрим, идёт ли на них стрим и запись
            response_ping = await ping_obs(ip, port, password)
            if not response_ping["error"]:
                stream_resp = await ping_stream(ip, port, password)

                if not stream_resp["error"] and stream_resp["data"]:
                    stream_status = True
                else:
                    stream_status = False

                recording_resp = await ping_recording(ip, port, password)

                if not recording_resp["error"] and recording_resp["data"]:
                    recording_status = True
                else:
                    recording_status = False

                resp[name] = {'ip': ip, 'port': port, 'availability': True, "stream_status": stream_status,
                              "recording_status": recording_status}
            else:
                resp[name] = {'ip': ip, 'port': port, 'availability': False}
        else:
            resp[name] = {'ip': ip, 'port': port}

    return JSONResponse(content=resp)


@app.get('/check_group_obs')
async def check_group_obs(request_body: CheckGroupObs):
    added_obs = await conductor.get_groups_obs(request_body.group_id)
    content = dict()  # словарь {'имя обс': {параметры}, 'имя обс-2': {параметры-2}, ...}
    for obs in added_obs:
        obs_name = obs[0]
        ip = obs[1]
        port = obs[2]
        content[obs_name] = {'ip': ip, 'port': port}

    return JSONResponse(content=content)


@app.get('/check_obs_groups')
async def check_obs_group(request_body: CheckObsGroups):
    ip, port, password = await db.get_obs_info(request_body.user_id, request_body.obs_name)
    groups = await db.find_obs_groups(ip, port)
    return JSONResponse(content=groups)


@app.post('/add_group')
async def add_group(request_body: AddGroup):
    """
    Добавляет в БД новую группу
    """
    logger.info('Adding group')
    await conductor.create_group_in_db(request_body.group_id)
    logger.info(f'Added group {request_body.group_id} to database')
    return JSONResponse(content={'group_id': request_body.group_id})


@app.post('/add_group_member')
async def add_group_member(request_body: AddGroupMember):
    """
    Добавляет в БД нового участника группы
    """
    logger.info('Adding group member')
    await conductor.add_groups_user(request_body.group_id, request_body.user_id, request_body.is_admin)
    logger.info(f'Added member {request_body.user_id} to group {request_body.group_id}')
    return JSONResponse(content={'group_id': request_body.group_id})


@app.delete('/delete_group_member')
async def delete_group_member(request_body: DeleteGroupMember):
    """
    Удаляет участника из группы
    """
    await conductor.del_group_user(request_body.group_id, request_body.user_id)
    logger.info(f'Deleting member {request_body.user_id} from group {request_body.group_id}')
    return JSONResponse(content={'group_id': request_body.group_id})


@app.post('/add_obs')
async def add_obs(request_body: UsersAddObs):
    logger.info('Adding users obs stand')
    await conductor.add_users_obs(request_body.user_id, request_body.obs_name,
                                  request_body.ip, request_body.port, request_body.password)
    logger.info(f'Added obs with ip {request_body.ip} for {request_body.user_id} in database')
    return JSONResponse(content={'text': 'Operation succeed'})


@app.post('/add_group_obs')
async def add_group_obs(request_body: AddGroupObs):
    content = {"added": [], "missed": []}
    for obs_name in request_body.obs_names:
        # Если ОБС найдена и добавлена, то added=True
        added = await conductor.add_groups_obs(request_body.group_id, request_body.admin_id, obs_name)
        if added:
            content["added"].append(obs_name)
        else:
            content["missed"].append(obs_name)
    return JSONResponse(content=content)


@app.get('/ping_obs')   # TODO: example 1
async def ping_obs_handler(request_body: UserPingStreamObs):
    # ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)
    # так больше не делаем

    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)
    resp = await ping_obs(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content={'text': 'Obs stand is unavailable'})

    return JSONResponse(content={'text': 'Obs stand is available'})




@app.get('/ping_stream')
async def ping_stream_handler(request_body: UserPingStreamObs):
    """
    Endpoint для проверки, работает ли стрим
    :return:
    """
    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)
    # if await ping_obs(ip, port, password):
    resp = await ping_stream(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    if not resp["data"]:
        return JSONResponse(status_code=451, content={'text': 'Stream on obs is not running'})

    resp = await stream_time(ip, port, password)

    if resp["error"]:
        logger.info(resp["error"])
        return JSONResponse(status_code=503, content=resp["error"])

    time = str(resp["data"])
    logger.info(time)

    return JSONResponse(content={'text': 'Stream on obs is running', 'stream_time': time})

    # else:
    #     return JSONResponse(status_code=409,
    #                         content={'text': 'OBS is not available'})


@app.get('/ping_recording')
async def ping_recording_handler(request_body: UserPingStreamObs):
    """
    Endpoint для проверки, работает ли запись
    :return:
    """
    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)
    # if await ping_obs(ip, port, password):
    resp = await ping_recording(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    if not resp["data"]:
        return JSONResponse(status_code=451, content={'text': 'Stream on obs is not running'})

    resp = await recording_time(ip, port, password)

    if resp["error"]:
        logger.info(resp["error"])
        return JSONResponse(status_code=503, content=resp["error"])

    time = str(resp["data"])
    logger.info(time)

    return JSONResponse(content={'text': 'Recording on obs is running', 'recording_time': time})
    # else:
    #     return JSONResponse(status_code=409,
    #                         content={'text': 'OBS is not available'})


@app.post('/plan_stream')
async def plan_stream(request_body: PlanStreamModel):
    interval_begin = datetime.datetime.strptime(request_body.date1,
                                                "%Y-%m-%d %H:%M:%S")
    interval_end = datetime.datetime.strptime(request_body.date2,
                                              "%Y-%m-%d %H:%M:%S")
    interval = await conductor.create_planned_stream(request_body.user_id, request_body.key,
                                                     interval_begin, interval_end,
                                                     request_body.obs_name)
    return JSONResponse(content={'text': f'Stream successfully planned in '
                                         f'interval {interval[0]} - '
                                         f'{interval[1]}'})


@app.post('/trigger_calendar_start_stream')
async def start_stream_calendar(calendar_data: CalendarData):
    """
    Запуск стрима через календарь, в этом эндпоинте необходимо передавать
    сразу все параметры для запуска стрима. Однако user_id не требуется
    {"ip": "111.11.11.11", "port": "1111",
     "password": "111111", "stream_key": "111111", "youtube_server": "http..x"}
    :param calendar_data:
    :return:
    """
    ip, port, password = calendar_data.ip, calendar_data.port, calendar_data.password
    resp = await stop_youtube_stream(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    resp = await set_stream_parameters(ip, port, password, calendar_data.stream_key, calendar_data.youtube_server)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    resp = await start_youtube_stream(ip, port, password, calendar_data.stream_key, calendar_data.youtube_server)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    return JSONResponse(content={'response': "started stream successfully"})


@app.post('/trigger_calendar_stop_stream')
async def stop_stream_calendar(calendar_data: CalendarDataStop):
    """
    Прекращение стрима через календарь, в этом эндпоинте необходимо передавать
    сразу все параметры (кроме ключа трансляции).
    User_id и stream_key передавать не нужно.
    {"ip": "111.11.11.11", "port": "1111", "password": "111111",
    "youtube_server": "http...a"}
    :param calendar_data:
    :return:
    """
    ip, port, password = calendar_data.ip, calendar_data.port, calendar_data.password
    resp = await stop_youtube_stream(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    return JSONResponse(content={'response': "stopped successfully"})


@app.get('/get_obs_info')
async def get_obs_info_handler(request_body: UserObs):
    """
    Возвращает информацию о данном стенде
    # {"user_id": "123", "obs_name": "obs_0"}
    :param request_body:
    :return:
    """
    ip, port, password = await db.get_obs_info(request_body.user_id,
                                               request_body.obs_name)
    return JSONResponse(content={'ip': ip, 'port': port, 'password': password})


@app.get('/set_scene')  #TODO: example 2
async def set_scene_handler(request_body: SetSceneModel):
    """
    Вызывает функцию установки выбранной сцены в Program, если она есть
    :param request_body:
    :return:
    """
    # ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)
    # так больше не делаем

    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)

    # if not await ping_obs(ip, port, password):
    #     return JSONResponse(status_code=409,
    #                         content='Obs stand is unavailable')
    resp = await get_scenes(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    if request_body.scene_name not in resp["data"]["all"]:
        return JSONResponse(status_code=404, content='There is no such scene')

    resp = await set_scene(ip, port, password, request_body.scene_name)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    return JSONResponse(content='The current scene is changed')


@app.get('/get_scenes')
async def get_scenes_handler(request_body: GetScenesModel):
    """
    Функция остановки записи (сама делает проверки и возвращает ошибку, если
    пользователя нет в базе данных т.е. не было register_user; также ошибка
    будет в случае, если obs с таким именем нет)
    # {"user_id": "123", "obs_name": "obs_0"}
    :param request_body:
    :return:
    """
    # ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)
    # так больше не делаем

    ip, port, password = await conductor.get_obs_info(request_body.user_id, request_body.obs_name)

    # if not await ping_obs(ip, port, password):
    #     return JSONResponse(status_code=409, content='Obs stand is unavailable')

    resp = await get_scenes(ip, port, password)

    if resp["error"]:
        return JSONResponse(status_code=503, content=resp["error"])

    return JSONResponse(content=resp["data"])


'''@app.post('/client_state')
async def set_client_state(request_body: ClientState):
    logger.info(request_body.time + ": " + "State of " + request_body.name + " is " +
                "UP" if request_body.state else "DOWN")
'''

'''@app.post('/set_new_ip')
async def set_new_ip_for_client(request_body: IpChange):
    logger.info(f"Ip was changed for {request_body.name} from {request_body.old_ip}:{request_body.port} to"
                f" {request_body.new_ip}:{request_body.port}")
'''