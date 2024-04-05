from aiogram import Bot
from aiogram.types import User
import requests
import json

from loguru import logger


async def send_group_notifications(bot: Bot, user: User, obs_name: str, type, date=None):
    """type: {'start_recording', 'stop_recording', 'start_stream', 'stop_stream', 'plan_stream'}"""
    body = {"user_id": user.id, "obs_name": obs_name}
    url = 'http://127.0.0.1:8000/check_obs_groups'
    response = requests.get(url, data=json.dumps(body))
    groups = response.json()
    name = f'@{user.username}' if user.username else str(user.id)
    # sends notification with user's username if username is specified otherwise, user_id
    if type == 'start_recording':
        text = f'''На OBS {obs_name} начата запись пользователем {name}.'''
    elif type == 'stop_recording':
        text = f'''На OBS {obs_name} остановлена запись пользователем {name}.'''
    elif type == 'start_stream':
        text = f'''На OBS {obs_name} начата трансляция пользователем {name}.'''
    elif type == 'stop_stream':
        text = f'''На OBS {obs_name} остановлена трансляция пользователем {name}.'''
    elif type == 'plan_stream':
        text = f'''На OBS {obs_name} запланирована трансяция на {date} пользователем {name}.'''
    else:
        raise KeyError
    for i in groups:
        try:
            await bot.send_message(i, text)
        except Exception as err:
            logger.debug(f'The message to the group {i} has not been sent.')

