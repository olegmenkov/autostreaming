import asyncio
from loguru import logger
import simpleobsws
import json
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from os import getenv


load_dotenv("../.env")
# MQTT broker configuration
MQTT_BROKER_HOST = getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(getenv("MQTT_BROKER_PORT"))
MQTT_USER = getenv("MQTT_USERNAME")
MQTT_PASSWORD = getenv("MQTT_PASSWORD")
MQTT_REQUEST_TOPIC = getenv("MQTT_REQUEST_TOPIC")
MQTT_RESPONSE_TOPIC = getenv("MQTT_RESPONSE_TOPIC")
RESPONSE = None
OBS_NAME = ""
global_lock = asyncio.Lock()

# Define MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)


async def run_obsws_request(obs_name: str, password: str, request: str, data: dict = None) -> dict:
    '''
    request form {
        request = "GetVersion",
        data = None
        password = "xxx"
    }

    response form {
        data = {...} / None,
        error = None / "error description"
    }
    '''
    global RESPONSE, OBS_NAME
    mqtt_client.loop_start()
    await asyncio.sleep(0.5)
    await global_lock.acquire()
    RESPONSE = None
    OBS_NAME = obs_name
    req = {
        "request": request,
        "data": data,
        "password": password
    }

    publish(mqtt_client, MQTT_REQUEST_TOPIC + "/" + obs_name, req)
    time_counter = 0
    while not RESPONSE and time_counter < 120:
        await asyncio.sleep(0.1)
        time_counter += 1

    local_rep = RESPONSE
    global_lock.release()
    mqtt_client.loop_stop()

    if local_rep:
        return local_rep
    else:
        return {"data": None, "error": "time limit exceeded"}


def on_connect(client, userdata, flags, rc):
    logger.info("Connected with result code "+str(rc))
    client.subscribe(MQTT_RESPONSE_TOPIC + "/#")


def publish(client, topic, data):
    msg = json.dumps(data)
    result = client.publish(topic, msg, qos=1)
    status = result[0]

    if status:
        logger.info(f"Failed to send message to topic {topic}")
    else:
        logger.info("SEND to topic:" + topic)


def on_message(client, userdata, msg):
    global RESPONSE

    resp = json.loads(msg.payload)
    if msg.topic == MQTT_RESPONSE_TOPIC + "/" + OBS_NAME:
        RESPONSE = resp


# Assign callbacks to client
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Connect to MQTT broker
mqtt_client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)


async def start_youtube_stream(ip, port, password, key: str, youtube_server: str = None):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS) и
    ключ трансляции. Начинает стрим на этой OBS с этим ключом
    """

    if youtube_server is None:
        youtube_server = "rtmp://a.rtmp.youtube.com/live2"

    obs_name = ip + f":{port}"
    request = 'SetStreamServiceSettings'
    # установим нужные настройки стрима:
    data = {"streamServiceSettings":
                {"bwtest": False,
                    "key": key,
                    "server": youtube_server,
                    "service": "YouTube - RTMPS"},
            "streamServiceType": "rtmp_common"}
    resp = await run_obsws_request(obs_name, password, request, data)

    if resp["error"]:
        return resp

    request = 'StartStream'
    resp = await run_obsws_request(obs_name, password, request)

    return resp


async def stop_youtube_stream(ip, port, password):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS).
    Заканчивает стрим на этой OBS
    """

    obs_name = ip + f":{port}"
    request = 'StopStream'
    resp = await run_obsws_request(obs_name, password, request)

    return resp


async def set_stream_parameters(ip, port, password, key: str, youtube_server: str = None):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS) и
    ключ трансляции. Устанавливает настройки этой OBS: тип трансляции,
    сервер, ключ
    """
    if youtube_server is None:
        youtube_server = "rtmp://a.rtmp.youtube.com/live2"

    obs_name = ip + f":{port}"
    request = 'SetStreamServiceSettings'
    # установим нужные настройки стрима:
    data = {"streamServiceSettings":
                {"bwtest": False,
                    "key": key,
                    "server": youtube_server,
                    "service": "YouTube - RTMPS"},
            "streamServiceType": "rtmp_common"}
    resp = await run_obsws_request(obs_name, password, request, data)

    return resp


async def start_recording(ip: str, port: str, password: str):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS).
    Начинает запись на этой OBS.
    """

    obs_name = ip + f":{port}"
    request = 'StartRecord'
    resp = await run_obsws_request(obs_name, password, request)

    return resp


async def stop_recording(ip: str, port: str, password: str):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS).
    Прекращает запись на этой OBS.
    """

    obs_name = ip + f":{port}"
    request = 'StopRecord'
    resp = await run_obsws_request(obs_name, password, request)

    return resp


async def ping_obs(ip: str, port: str, password: str):
    """
    Отправляет запрос на получение статистики. Если это удаётся сделать, возвращает True
    Если нет, то False
    """
    '''try:
        await obsclient.connect()
        await obsclient.wait_until_identified()

        request = simpleobsws.Request('GetStats')  # запрос "посмотреть статистику"
        ret = await obsclient.call(request)  # запускаем его

        await obsclient.disconnect()
        return True
    except Exception as err:
        return False'''

    # Вместо формирования вебсокета прям тут - отправляем в приложение по MQTT ip, port, password, тип запроса
    # приложение формирует obsclient (см. conductor.get_obs_client)
    # и отправляет в него вебсокет (см. выше)
    # return должен быть таким же


async def ping_stream(ip, port, password) -> bool:
    """
    Проверяет статус стрима на обс-клиенте
    Возвращает True, если стрим идёт, и False -- если нет
    """
    obs_name = ip + f":{port}"
    request = 'GetStreamStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return False

    return resp["data"]['outputActive']


async def stream_time(ip, port, password):
    """
    Проверяет время записи на обс-клиенте
    """
    obs_name = ip + f":{port}"
    request = 'GetStreamStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return resp

    return resp["data"]['outputTimecode']


async def ping_recording(ip, port, password) -> bool:
    """
    Проверяет статус записи на обс-клиенте
    Возвращает True, если запись идёт, и False -- если нет
    """
    obs_name = ip + f":{port}"
    request = 'GetRecordStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return False

    return resp["data"]['outputActive']


async def recording_time(ip: str, port: str, password: str):
    """
    Проверяет время записи на обс-клиенте
    """

    obs_name = ip + f":{port}"
    request = 'GetRecordStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return resp

    return resp["data"]['outputTimecode']


async def get_scenes(ip: str, port: str, password: str):
    """
    Возвращает текущую сцену и список остальных
    """

    obs_name = ip + f":{port}"
    request = 'GetSceneList'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return resp

    ret = resp["data"]
    all_scenes = [item['sceneName'] for item in ret['scenes']]
    return {'current': ret['currentProgramSceneName'], 'all': all_scenes}

    # Вместо формирования вебсокета прям тут - отправляем в приложение по MQTT ip, port, password, тип запроса
    # приложение формирует obsclient (см. conductor.get_obs_client)
    # и отправляет в него вебсокет (см. выше)
    # return должен быть таким же


async def set_scene(ip: str, port: str, password: str, scene_name: str):
    """
    Устанавливает сцену с именем scene_name в Program выход
    """

    obs_name = ip + f":{port}"
    request = 'SetCurrentProgramScene'
    data = {'sceneName': scene_name}
    resp = await run_obsws_request(obs_name, password, request, data)

    return resp
    # Вместо формирования вебсокета прям тут - отправляем в приложение по MQTT ip, port, password, тип запроса
    # И requestData!
    # приложение формирует obsclient (см. conductor.get_obs_client)
    # и отправляет в него вебсокет (см. выше)
    # return должен быть таким же


async def main():
    ip = '172.18.191.11'
    port = '4445'
    pswd = 'GPDNoXkbTqy6RIcH'
    key = "yv5r-4rb1-kete-7hbk-a8z5"
    parameters = simpleobsws.IdentificationParameters(
        ignoreNonFatalRequestChecks=False)

    obsclient = simpleobsws.WebSocketClient(url='ws://' + ip + ':' + port,
                                            password=pswd,
                                            identification_parameters=parameters)

    print(await ping_obs(obsclient))


if __name__ == "__main__":
    asyncio.run(main())
