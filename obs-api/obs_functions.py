import asyncio
from loguru import logger
import simpleobsws
import json
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from os import getenv

# get all creds for mqtt
load_dotenv("../.env")
MQTT_BROKER_HOST = getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(getenv("MQTT_BROKER_PORT"))
MQTT_USER = getenv("MQTT_USERNAME")
MQTT_PASSWORD = getenv("MQTT_PASSWORD")
MQTT_REQUEST_TOPIC = getenv("MQTT_REQUEST_TOPIC")
MQTT_RESPONSE_TOPIC = getenv("MQTT_RESPONSE_TOPIC")
# RESPONSE - transit variable for moving data out of mqtt back-tread
RESPONSE = None
# OBS_NAME - transit variable for moving data into mqtt back-tread
OBS_NAME = ""
# global_lock - main locker for handle access race for transit variables RESPONSE and OBS_NAME
global_lock = asyncio.Lock()

# Define MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)


async def run_obsws_request(obs_name: str, password: str, request: str, data: dict = None) -> dict:
    """
    Send request to mqtt special request topic and wait for response
    request
    {
        "request": str (like "GetVersion"),
        "data": dict (like {"scene": scene_name})
        "password" = str
    }

    :param obs_name: name of obs that will execute request (like "172.32.4.20:4455")
    :param password: obsws password
    :param request: obsws request (like 'GetVersion')
    :param data: obsws reques additional data (like {"scene": scene_name})

    :return:
    {
        "data": responseData / None,
        "error": None / "wrong password" / f"failed on remote command:{req}\nwith data:{data}"
    }
    """
    global RESPONSE, OBS_NAME
    mqtt_client.loop_start()
    # wait to connect
    await asyncio.sleep(0.5)
    # lock RESPONSE and OBS_NAME variables
    await global_lock.acquire()
    RESPONSE = None
    OBS_NAME = obs_name
    req = {
        "request": request,
        "data": data,
        "password": password
    }
    # publish request to mqtt special request topic
    publish(mqtt_client, MQTT_REQUEST_TOPIC + "/" + obs_name, req)
    # time_counter - set time limit 4s for response
    time_counter = 0
    # wait until response or time limit
    while not RESPONSE and time_counter < 40:
        await asyncio.sleep(0.1)
        time_counter += 1
    # move information to local variable for releasing RESPONSE transit variable
    local_rep = RESPONSE
    global_lock.release()
    mqtt_client.loop_stop()

    if local_rep:
        return local_rep
    else:
        return {"data": None, "error": "time limit exceeded"}


def on_connect(client: mqtt.Client, userdata, flags, rc):
    """
    Callback function for mqtt client, execute when try to connect to mqtt broker
    Subscribe client to autostream response topics
    """
    logger.info("Connected with result code "+str(rc))
    client.subscribe(MQTT_RESPONSE_TOPIC + "/#")


def publish(client: mqtt.Client, topic: str, data: dict):
    """
    Publish obsws request to mqtt broker on special request topic (like autorstreaming/request/174.32.4.28:4455)
    :param data:{
                    "request": str (like "GetVersion"),
                    "data": dict (like {"scene": scene_name})
                    "password" = str
                }
    """
    msg = json.dumps(data)
    result = client.publish(topic, msg, qos=1)
    status = result[0]

    if status:
        logger.info(f"Failed to send message to topic {topic}")
    else:
        logger.info("SEND to topic:" + topic)


def on_message(client, userdata, msg):
    """
    Callback function for mqtt client, execute when message published to mqtt broker subscribed topic
    Gets obsws response and pass it in RESPONSE global variable that allows pass response out of back tread to
    async function run_obsws_request()
    response {
            "obs_name": str (like 172.23.5.20:4455)
            "fails": {scene_name:[failed_source_name, ...], ...}
         }
    """
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
    obs_name = ip + f":{port}"
    request = 'GetStats'
    resp = await run_obsws_request(obs_name, password, request)

    return resp

    # Вместо формирования вебсокета прям тут - отправляем в приложение по MQTT ip, port, password, тип запроса
    # приложение формирует obsclient (см. conductor.get_obs_client)
    # и отправляет в него вебсокет (см. выше)
    # return должен быть таким же


async def ping_stream(ip, port, password):
    """
    Проверяет статус стрима на обс-клиенте
    Возвращает True, если стрим идёт, и False -- если нет
    """
    obs_name = ip + f":{port}"
    request = 'GetStreamStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return resp

    return {"data": resp["data"]['outputActive'], "error": None}


async def stream_time(ip, port, password):
    """
    Проверяет время записи на обс-клиенте
    """
    obs_name = ip + f":{port}"
    request = 'GetStreamStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return resp

    return {"data": resp["data"]['outputTimecode'], "error": None}


async def ping_recording(ip, port, password):
    """
    Проверяет статус записи на обс-клиенте
    Возвращает True, если запись идёт, и False -- если нет
    """
    obs_name = ip + f":{port}"
    request = 'GetRecordStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return resp

    return {"data": resp["data"]['outputActive'], "error": None}


async def recording_time(ip: str, port: str, password: str):
    """
    Проверяет время записи на обс-клиенте
    """

    obs_name = ip + f":{port}"
    request = 'GetRecordStatus'
    resp = await run_obsws_request(obs_name, password, request)

    if resp["error"]:
        return resp

    return {"data": resp["data"]['outputTimecode'], "error": None}


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

    return {"data": {'current': ret['currentProgramSceneName'], 'all': all_scenes}, "error": None}

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
