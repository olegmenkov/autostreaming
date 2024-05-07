import json
import os
import asyncio
import time

import emoji
import paho.mqtt.client as mqtt
import requests

from aiogram import Bot, Dispatcher
from aiogram.types import bot_command_scope_all_private_chats, bot_command_scope_all_chat_administrators
from cffi.model import global_lock
from dotenv import load_dotenv
from loguru import logger

import commands
import private_handlers, group_handlers
from private_handlers import enter


load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN)

DATA = None


async def send_error_notifications(bot: Bot, mqtt_client):
    global DATA
    mqtt_client.loop_start()
    await asyncio.sleep(0.5)
    await global_lock.acquire()
    DATA = None

    time_counter = 0
    while not DATA and time_counter < 40:
        await asyncio.sleep(0.1)
        time_counter += 1

    data = DATA
    global_lock.release()
    mqtt_client.loop_stop()

    if data:
        for obs_name in data:
            obs_info = data[obs_name]
            errors = dict()
            for scene_name in obs_info:
                scene_info = obs_info[scene_name]
                for record in scene_info:
                    if not record["state"]:
                        errors[scene_name] = [record["source"]] if scene_name not in errors else errors[
                            scene_name].append(record["source"])
            if errors:
                ip, port = obs_name.split(':')
                body = {"ip": ip, "port": port}
                url = 'http://127.0.0.1:8000/check_obs_groups_notifications'
                response = requests.get(url, data=json.dumps(body))
                groups = response.json()
                logger.info(groups)

                for record in groups:
                    group_id, obs_name = record["group_id"], record["obs_name"]
                    text = f"{emoji.emojize(':warning:')} В OBS {obs_name} обнаружены проблемы. {enter}"
                    for scene_name in errors:
                        text += f"В сцене {scene_name}: {', '.join(errors[scene_name])}. {enter}"
                    try:
                        await bot.send_message(group_id, text)
                    except Exception as err:
                        logger.debug(f'The message to the group {group_id} has not been sent.')
    else:
        logger.debug('Time limit exceeded')


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("autostream/#")


# для отправки сообщения в topic
def publish(client, topic):
    # обязательно переводить в json-строку!
    # сообщение PING_OBS вызывает функцию пингования источников на клиентской обс
    msg = json.dumps("PING_OBS")
    result = client.publish(topic, msg)
    status = result[0]
    if not status:
        print(f"Send {msg} to {topic}")
    else:
        print(f"Failed to send message to topic {topic}")


# callback на появление сообщения в topic
def on_message(client, userdata, msg):
    '''
        {OBS_NAME: {
                scene_name: [ {"source": source_name, "state": True}, {"source": source_name2, "state": False}, {}],
                scene_name2: [ {}, {}, {}],
                ...
                }
    }

    OBS_NAME = OBSWS_HOST:OBSWS_PORT
    Пример: 172.45.55.34:4455
    '''

    if json.loads(msg.payload) != "PING_OBS":
        data = json.loads(msg.payload)
        logger.info(data)
        global DATA
        DATA = data


async def main():
    # logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    # Dispatcher is a root router
    dp = Dispatcher()
    # ... and all other routers should be attached to Dispatcher
    await bot.delete_webhook(drop_pending_updates=True)
    dp.include_routers(private_handlers.router,
                       group_handlers.router)
    # Команды из menu
    await bot.set_my_commands(commands=commands.private_commands,
                              scope=bot_command_scope_all_private_chats.BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands=commands.group_commands,
                              scope=bot_command_scope_all_chat_administrators.BotCommandScopeAllChatAdministrators())
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    # And the run events dispatching

    await dp.start_polling(bot, skip_updates=True, allowed_updates=['message', 'my_chat_member', 'callback_query',
                                                                    # 'video', 'photo', 'audio', 'document',
                                                                    'text',
                                                                    # 'caption',
                                                                    'chat_member'])

    topic = "autostream/ping_sources"
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # имя и пароль хранятся в локальных переменных!
    load_dotenv()
    USERNAME = os.getenv("NAME")
    PASSWORD = os.getenv("PASSWORD")

    client.username_pw_set(USERNAME, PASSWORD)

    # connect_async to allow background processing
    client.connect_async("172.18.130.40", 1883, 60)
    client.loop_start()

    # тут нужно написать цикл для отправки сообщений в topic
    while True:
        time.sleep(1)
        publish(client, topic)
        await send_error_notifications(bot, client)


if __name__ == '__main__':
    asyncio.run(main())
