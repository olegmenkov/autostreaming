import asyncio
from loguru import logger
import simpleobsws
import time
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


async def start_youtube_stream(obsclient: simpleobsws.WebSocketClient,
                               key: str, youtube_server: str = None):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS) и
    ключ трансляции. Начинает стрим на этой OBS с этим ключом
    """

    if youtube_server is None:
        youtube_server = "rtmp://a.rtmp.youtube.com/live2"
    await obsclient.connect()
    await obsclient.wait_until_identified()

    # установим нужные настройки стрима:
    request = simpleobsws.Request('SetStreamServiceSettings',
                                  requestData={
                                      "streamServiceSettings":
                                          {"bwtest": False,
                                           "key": key,
                                           "server": youtube_server,
                                           "service": "YouTube - RTMPS"},
                                      "streamServiceType": "rtmp_common"})

    ret = await obsclient.call(request)  # отправляем запрос
    if ret.ok():  # проверка
        logger.info("Request 'start stream' succeeded!")

    request = simpleobsws.Request('StartStream')  # запрос "начать стрим"
    ret = await obsclient.call(request)  # запускаем его
    if ret.ok():  # проверка
        logger.info("Request 'start stream' succeeded!")

    await obsclient.disconnect()


async def stop_youtube_stream(obsclient: simpleobsws.WebSocketClient):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS).
    Заканчивает стрим на этой OBS
    """
    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('StopStream')  # запрос "остановить стрим"
    ret = await obsclient.call(request)  # запускаем его
    if ret.ok():  # проверка
        logger.info("Request 'stop stream' succeeded!")

    await obsclient.disconnect()


async def set_stream_parameters(obsclient: simpleobsws.WebSocketClient,
                                key: str, youtube_server: str = None):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS) и
    ключ трансляции. Устанавливает настройки этой OBS: тип трансляции,
    сервер, ключ
    """
    if youtube_server is None:
        youtube_server = "rtmp://a.rtmp.youtube.com/live2"
    await obsclient.connect()
    await obsclient.wait_until_identified()

    # установим нужные настройки стрима:
    request = simpleobsws.Request('SetStreamServiceSettings', requestData={
        "streamServiceSettings":
            {"bwtest": False,
             "key": key,
             "server": youtube_server,
             "service": "YouTube - RTMPS"},
        "streamServiceType": "rtmp_common"})

    ret = await obsclient.call(request)  # отправляем запрос
    if ret.ok():  # проверка
        logger.info("Request 'start stream' succeeded!")

    await obsclient.disconnect()


async def start_recording(obsclient: simpleobsws.WebSocketClient):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS).
    Начинает запись на этой OBS.
    """

    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('StartRecord')  # запрос "начать стрим"
    ret = await obsclient.call(request)  # запускаем его
    if ret.ok():  # проверка
        logger.info("Request 'start record' succeeded!")

    await obsclient.disconnect()


async def stop_recording(obsclient: simpleobsws.WebSocketClient):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS).
    Прекращает запись на этой OBS.
    """

    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('StopRecord')  # запрос "начать стрим"
    ret = await obsclient.call(request)  # запускаем его
    if ret.ok():  # проверка
        logger.info("Request 'stop record' succeeded!")

    await obsclient.disconnect()


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


async def ping_stream(obsclient: simpleobsws.WebSocketClient):
    """
    Проверяет статус стрима на обс-клиенте
    Возвращает True, если стрим идёт, и False -- если нет
    """
    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('GetStreamStatus')  # запрос "посмотреть статистику"
    ret = await obsclient.call(request)  # запускаем его
    await obsclient.disconnect()

    return ret.responseData['outputActive']


async def stream_time(obsclient: simpleobsws.WebSocketClient):
    """
    Проверяет время записи на обс-клиенте
    """
    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('GetStreamStatus')  # запрос "посмотреть статистику"
    ret = await obsclient.call(request)  # запускаем его

    await obsclient.disconnect()

    return str(ret.responseData['outputTimecode'])


async def ping_recording(obsclient: simpleobsws.WebSocketClient):
    """
    Проверяет статус записи на обс-клиенте
    Возвращает True, если запись идёт, и False -- если нет
    """
    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('GetRecordStatus')  # запрос "посмотреть статистику"
    ret = await obsclient.call(request)  # запускаем его

    await obsclient.disconnect()

    return ret.responseData['outputActive']


async def recording_time(obsclient: simpleobsws.WebSocketClient):
    """
    Проверяет время записи на обс-клиенте
    """
    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('GetRecordStatus')  # запрос "посмотреть статистику"
    ret = await obsclient.call(request)  # запускаем его

    await obsclient.disconnect()
    return str(ret.responseData['outputTimecode'])


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

    """await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('SetCurrentProgramScene', requestData={'sceneName': scene_name})
    ret = await obsclient.call(request)  # запускаем его

    await obsclient.disconnect()"""

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
