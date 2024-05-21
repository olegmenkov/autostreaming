import json
import os
import asyncio
import emoji
import paho.mqtt.client as mqtt
import requests
from aiogram import Bot, Dispatcher
from aiogram.types import bot_command_scope_all_private_chats, bot_command_scope_all_chat_administrators
from dotenv import load_dotenv
from loguru import logger
import commands
import private_handlers, group_handlers
from private_handlers import enter


load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
# MQTT broker configuration
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))
MQTT_USER = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_PING_TOPIC = os.getenv("MQTT_PING_TOPIC")
# Define MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)


def on_connect(client, userdata, flags, rc):
    logger.info("Connected with result code "+str(rc))
    client.subscribe(MQTT_PING_TOPIC)


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
    logger.info("GOT MESSAGE")
    data = json.loads(msg.payload)
    logger.info(data)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(send_error_notifications(data))


async def send_error_notifications(data: dict):
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
    logger.info(response)
    groups = response.json()
    logger.info(groups)

    for record in groups:
        group_id, obs_name = record["group_id"], record["obs_name"]
        text = f"{emoji.emojize(':warning:')} В OBS {obs_name} обнаружены проблемы. {enter}"
        for scene_name in data["fails"]:
            text += f"В сцене {scene_name}: {', '.join(data['fails'][scene_name])}. {enter}"

        try:
            await bot.send_message(group_id, text)
        except Exception as err:
            logger.debug(f'The message to the group {group_id} has not been sent.')
            logger.error(err)


async def main():
    global bot
    logger.info("RUN MAIN")
    bot = Bot(token=BOT_TOKEN)
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


if __name__ == '__main__':
    # Connect to MQTT broker
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    mqtt_client.loop_start()
    asyncio.run(main())

