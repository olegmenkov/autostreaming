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


async def send_error_notifications(bot: Bot, data: dict):
    '''
    data
    {
        "obs_name": obs_name
        "fails": {scene_name:[failed_source_name, ...], ...}
    }
    '''
    obs_name = data["obs_name"]
    ip, port = obs_name.split(':')
    body = {"ip": ip, "port": port}
    url = 'http://127.0.0.1:8000/check_obs_groups_notifications'
    response = requests.get(url, data=json.dumps(body))
    groups = response.json()
    logger.info(groups)

    for record in groups:
        group_id, obs_name = record["group_id"], record["obs_name"]
        text = f"{emoji.emojize(':warning:')} В OBS {obs_name} обнаружены проблемы. {enter}"
        for scene_name in data["fails"]:
            text += f"В сцене {scene_name}: {', '.join(data[scene_name])}. {enter}"
        try:
            await bot.send_message(group_id, text)
        except Exception as err:
            logger.debug(f'The message to the group {group_id} has not been sent.')


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("autostream/ping_sources")


# callback на появление сообщения в topic
def on_message(client, userdata, msg):
    '''
    msg
    {
        "obs_name": obs_name
        "fails": {scene_name:[failed_source_name, ...], ...}
    }

    obs_name = obsws_host:obsws_port
    Пример: 172.45.55.34:4455
    '''
    data = json.loads(msg.payload)
    logger.info(data)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(send_error_notifications(bot, data))


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


if __name__ == '__main__':
    asyncio.run(main())
