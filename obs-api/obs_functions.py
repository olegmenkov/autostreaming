import asyncio
from loguru import logger
import simpleobsws
import time


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


async def ping_obs(obsclient: simpleobsws.WebSocketClient):
    """
    Принимает объект класса simpleobsws.WebSocketClient (OBS).
    Отправляет запрос. Если это удаётся сделать, возвращает True
    Если нет, то False
    """
    try:
        await obsclient.connect()
        await obsclient.wait_until_identified()

        request = simpleobsws.Request('GetStats')  # запрос "посмотреть статистику"
        ret = await obsclient.call(request)  # запускаем его

        await obsclient.disconnect()
        return True
    except Exception as err:
        return False


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


async def get_scenes(obsclient: simpleobsws.WebSocketClient):
    """
    Возвращает текущую сцену и список остальных
    """

    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('GetSceneList')
    ret = await obsclient.call(request)  # запускаем его

    await obsclient.disconnect()
    all_scenes = [item['sceneName'] for item in ret.responseData['scenes']]

    return {'current': ret.responseData['currentProgramSceneName'], 'all': all_scenes}


async def set_scene(obsclient: simpleobsws.WebSocketClient, scene_name: str):
    """
    Устанавливает сцену с именем scene_name в Program выход
    """

    await obsclient.connect()
    await obsclient.wait_until_identified()

    request = simpleobsws.Request('SetCurrentProgramScene', requestData={'sceneName': scene_name})
    ret = await obsclient.call(request)  # запускаем его

    await obsclient.disconnect()


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
