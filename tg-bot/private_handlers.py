from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.types import Message, bot_command_scope_all_private_chats, bot_command_scope_all_chat_administrators, \
    InlineKeyboardButton, InlineKeyboardMarkup
import requests
import json
import uuid
import datetime
from loguru import logger
import emoji
from aiogram import Bot, Dispatcher, Router, F
import group_notifications
# from group_notifications import TEST
from filters import ChatTypeFilter

router = Router()
router.message.filter(ChatTypeFilter(chat_type=["private"]))

enter = """
"""
# с русского на язык БД
fields_db = {"Название": "obs_name", "IP": "ip", "Порт": "port", "Пароль": "password"}


class Form(StatesGroup):
    """
    Перечисляем состояния, в которые
    может переходить машина (бот)
    """

    add_obs = State()

    # Для удаления ОБС
    delete_obs = State()
    delete_obs_confirmed = State()

    check_obs = State()

    # Для редактирования OBS
    select_obs_edit_obs = State()
    select_field = State()
    get_new_value = State()

    # Для начала стрима
    select_obs_start_stream = State()
    select_server_key = State()

    # Для остановки стрима
    stop_stream = State()
    stop_stream_confirmed = State()

    plan_stream = State()
    start_recording = State()

    # Для остановки записи
    stop_recording = State()
    stop_recording_confirmed = State()

    ping_recording = State()
    ping_obs = State()
    ping_stream = State()
    schedule_of_obs = State()
    get_scenes = State()

    # для установки сцен
    select_obs_set_scene = State()
    select_scene = State()

    # для планирования стрима:
    select_name = State()
    select_date = State()
    select_key = State()
    select_youtube_server = State()
    select_obs_plan_stream = State()

    # для планирования записи
    select_name_plan_recording = State()
    select_date_plan_recording = State()
    select_obs_plan_recording = State()

    # для планирования стрима+записи:
    select_name_plan_stream_rec = State()
    select_date_plan_stream_rec = State()
    select_key_plan_stream_rec = State()
    select_youtube_server_plan_stream_rec = State()
    select_obs_plan_stream_rec = State()


async def send_data_to_calendar(message, state):
    stream_data = await state.get_data()
    # отправляем запрос в календарь:
    def create_params(stream_data):
        return {key: stream_data[key] for key in stream_data}
    
    stream_data = {
        "start": stream_data['date1'],
        "stop": stream_data['date2'],
        "YT_server": stream_data['youtube_server'],
        "key_obs": stream_data['key'],
        "name": stream_data['name'],
        "ip_obs": stream_data['ip'],
        "port_obs": stream_data['port'],
        "password_obs": stream_data['password'],
    }
   
    # body = {"params" :{"start": stream_data['date1'], "stop": stream_data['date2'], "YT_server": stream_data['youtube_server'],
    #         "key_obs": stream_data['key'],
    #         "name": stream_data['name'], "ip_obs": stream_data['ip'], "port_obs": stream_data['port'],
    #         "password_obs": stream_data['password']}}
    url = "https://crm.miem.tv/telegram/calendar/create"
    response = requests.post(url, json = stream_data)
    logger.info(f'Sent {str(params)} and received {str(response.status_code)}')

    if response.status_code == 200:
        data = response.json()['result']
        if not data['success']:
            logger.info(str(response.content))
            if 'reserved' in data['data']:
                event_start = data["event.start"]
                event_stop = data["event.stop"]
                await message.answer(
                    f"Событие не может быть создано, так как на этом стенде уже запланирован стрим на время {event_start} - {event_stop}. Пожалуйста, введите даты заново.")
                await state.set_state(Form.select_date)
        else:
            await message.answer('Стрим запланирован.')
    else:
        logger.info(str(response.content))
        await message.answer("""Произошла ошибка. Возможно, сервис планирования временно недоступен.
Вы можете нажать /start и попробовать выполнить команду снова.""")


# Вывод клавиатуры со всеми добавленными OBS
async def show_obs_keyboard(message, state):
    user_id = message.from_user.id

    # получаем список OBS, чтобы добавить на кнопки

    response = requests.get('http://127.0.0.1:8000/check_obs', data=json.dumps({"user_id": user_id, "need_availability": False}))
    if response.status_code == 200:
        data = response.json()
        obs_names = [obs_name for obs_name in data]  # нам нужны только названия ОБС, они являются ключами

        # Добавляем их на кнопки
        if len(obs_names) == 0:
            await message.answer(
                'У вас ещё нет стендов с OBS. Вы можете добавить их командой /add_obs.')
            logger.info(f'There are no stands for user {user_id}')
        else:
            # делаем массив из строчек по 3 кнопки в каждой
            buttons = [KeyboardButton(text=str(obs_names[i])) for i in range(len(obs_names))]
            buttons = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
            buttons.append([KeyboardButton(text='Отмена')])
            # Создаем клавиатуру
            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

            # Отправляем сообщение с клавиатурой
            await message.answer('Выберите стенд с OBS:', reply_markup=keyboard)
            logger.info('Formed a keyboard, asked to choose obs')

    else:
        logger.debug(f'Error with user id "{user_id}"')
        await message.answer("""Произошла ошибка.
Вы можете нажать /start и попробовать выполнить команду снова.""")


# Вывод клавиатуры со сценами для OBS
async def show_scenes_keyboard(obs_name, message, state):
    user_id = message.from_user.id

    # получаем список OBS, чтобы добавить на кнопки

    response = requests.get('http://127.0.0.1:8000/get_scenes',
                            data=json.dumps({"user_id": user_id, "obs_name": obs_name}))
    logger.info(f'Sent user_id and obs_name and received {str(response.status_code)}')
    logger.info(f'{str(response.content)}')

    if response.status_code == 200:
        data = response.json()  # получаем данные в формате JSON
        all_scenes = data["all"]
        if len(all_scenes) == 0:
            await message.answer('На данном OBS ещё нет сцен.', reply_markup=types.ReplyKeyboardRemove())
            state.clear()
        else:
            # делаем массив из строчек по 3 кнопки в каждой
            buttons = [KeyboardButton(text=str(all_scenes[i])) for i in range(len(all_scenes))]
            buttons = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
            buttons.append([KeyboardButton(text='Отмена')])

            # формируем из него клавиатуру
            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

            # Отправляем сообщение с клавиатурой
            await message.answer('Выберите сцену:', reply_markup=keyboard)
            logger.info('Formed a keyboard, asked to choose a scene')

    elif response.status_code == 409:
        await message.answer(
            """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 404:
        await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                             reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("""Произошла ошибка.
    Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs.
    Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())


async def show_fields_keyboard(message, state):
    buttons = [[KeyboardButton(text='Название'), KeyboardButton(text='IP'), KeyboardButton(text='Порт'), KeyboardButton(text='Пароль')],
               [KeyboardButton(text='Отмена')]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer('Выберите параметр, который хотите изменить:', reply_markup=keyboard)
    logger.info('Formed a keyboard, asked to choose a field')


async def show_yes_no_keyboard(message, state, purpose):
    buttons = [[KeyboardButton(text='Да'), KeyboardButton(text='Нет')]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer('Вы действительно хотите '+purpose+'?', reply_markup=keyboard)
    logger.info('Formed a keyboard, asked to confirm')


ikb_cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Отмена', callback_data='cancel_fsm')]
])


@router.callback_query((F.data == 'cancel_fsm'))
async def name(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await call.answer()
    await call.message.answer('Действие отменено.', reply_markup=types.ReplyKeyboardRemove())


@router.message((F.text == 'Отмена'))
async def start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await message.answer('Действие отменено.', reply_markup=types.ReplyKeyboardRemove())


# @router.message((F.text == '/test'))
# async def start(message: Message):
#     await message.answer(TEST)


@router.message((F.text == '/start'))
async def start(message: Message):
    """
    Функция, которая вызывается при команде start
    """

    logger.info('Received the start command')
    user_id = message.from_user.id
    body = {"user_id": user_id}
    url = 'http://127.0.0.1:8000/register_user'  # регистрируем нового пользователя
    response = requests.post(url, data=json.dumps(body))
    logger.info(f'Sent {body} and received {str(response.status_code)}')
    logger.info(f'Sent {body} and received {str(response.content)}')

    if response.status_code != 200:
        await message.answer('Произошла ошибка. Пожалуйста, обратитесь к команде проекта СВТ-31.')

    await message.reply("""Добрый вечер!
Вы можете выбрать нужную команду.""")


@router.message((F.text == '/help'))
async def start(message: Message):
    """
    Функция, которая вызывается при команде help
    и выводит функционал бота
    """

    logger.info('Received the help command')

    await message.reply("""Функционал бота. 

/start - Начать работу с ботом 

Управление стендами с OBS:
/add_obs - Добавить стенд с OBS
/edit_obs - Редактировать стенд с OBS 
/delete_obs - Удалить стенд с OBS 
/check_obs - Показать все добавленные OBS
/ping_obs - Проверить доступность стенда с OBS 

Управление трансляциями:
/plan_stream - Запланировать стрим
/start_stream - Запустить стрим вручную прямо сейчас 
/stop_stream - Остановить стрим вручную прямо сейчас 
/ping_stream - Проверить, запущен ли стрим 

Управление записью:
/start_recording - Запустить запись
/stop_recording - Остановить запись
/ping_recording - Проверить, запущена ли запись

Управление сценами:
/get_scenes - Посмотреть информацию о сценах
/set_scene - Переключить сцену в Program
""")


@router.message((F.text == '/add_obs'))
async def add_obs(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "считать данные о новом ОБС"
    """

    logger.info('Received the add_obs command')
    await state.set_state(Form.add_obs)
    await message.answer("""Введите данные для нового стенда: имя, ip, порт и пароль с новой строки.
Например:""")
    await message.answer("""obs_1
172.18.191.1
4445
ekej323oi1""", reply_markup=ikb_cancel)


@router.message((F.text == '/edit_obs'))
async def edit_obs(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "выбрать обс для редактирования"
    """

    logger.info('Received the edit_obs command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.select_obs_edit_obs)


@router.message((F.text == '/delete_obs'))
async def delete_obs(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "удалить ОБС"
    """

    logger.info('Received the delete_obs command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.delete_obs)


@router.message((F.text == '/check_obs'))
async def check_obs(message: Message, state: FSMContext):
    """
     Переводит бота в состояние "показывает доступные ОБС у пользователя"
     """

    logger.info('Received the check_obs command')
    await message.answer('Мы ищем все ваши OBS и проверяем их доступность. Это займёт несколько секунд...')
    user_id = message.from_user.id
    body = {"user_id": user_id, "need_availability": True}
    url = 'http://127.0.0.1:8000/check_obs'
    response = requests.get(url, data=json.dumps(body))
    logger.info(f'Sent user_id and received {str(response.content)}')

    if response.status_code == 200:
        data = response.json()
        if len(data) == 0:
            answer = 'У вас ещё нет добавленных стендов с OBS. Вы можете добавить их командой /add_obs.'
        else:
            answer = 'Добавленные вами стенды с OBS:'
            for obs_name in data:
                ip = data[obs_name]["ip"]
                port = data[obs_name]["port"]
                answer += enter + f'{obs_name} ({ip}:{port})'
                # если ОБС недоступен, указываем это:
                if not data[obs_name]["availability"]:
                    answer += " - недоступен"
                # если доступен, показываем, идёт ли стрим и запись:
                else:
                    stream_status = data[obs_name]["stream_status"]
                    recording_status = data[obs_name]["recording_status"]
                    if stream_status:
                        answer += " " + emoji.emojize(":movie_camera:")
                    if recording_status:
                        answer += " " + emoji.emojize(":red_circle:")
        # в конце добавляем условные обозначения:
        answer += enter + enter + emoji.emojize(":movie_camera:") + ' - идёт стрим, ' + emoji.emojize(":red_circle:") + ' - идёт запись.'
        await message.answer(answer)
    else:
        await message.answer('Произошла ошибка. Попробуйте выполнить команду /start, а затем повторить /check_obs.')


@router.message(Command(commands=['start_stream']))
async def start_stream(message: Message, state: FSMContext):
    """
    Переключает бота в состояние "Начать стрим"
    """

    logger.info('Received the start_stream command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.select_obs_start_stream)


@router.message(Command(commands=['plan_stream']))
async def plan_stream(message: Message, state: FSMContext):
    """
    Переключает бота в состояние "Выбрать дату для планирования"
    """

    logger.info('Received the plan_stream command')
    await state.set_state(Form.select_name)
    await message.answer('Дайте название этой трансляции. Например, "Защиты в аудитории 306"', reply_markup=ikb_cancel)


@router.message(Command(commands=['plan_recording']))
async def plan_stream(message: Message, state: FSMContext):
    """
    Переключает бота в состояние "Выбрать дату для планирования"
    """

    logger.info('Received the plan_recording command')
    await state.set_state(Form.select_name_plan_recording)
    await message.answer('Дайте название этой записи. Например, "Защиты в аудитории 306"', reply_markup=ikb_cancel)



@router.message(Command(commands=['stop_stream']))
async def stop_stream(message: Message, state: FSMContext):
    """
    Переключает бота в состояние "Остановить стрим"
    """

    logger.info('Received the stop_stream command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.stop_stream)


@router.message(Command(commands=['start_recording']))
async def start_recording(message: Message, state: FSMContext):
    """
    Переключает бота в состояние "Начать запись"
    """

    logger.info('Received the start_recording command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.start_recording)


@router.message(Command(commands=['stop_recording']))
async def stop_recording(message: Message, state: FSMContext):
    """
    Переключает бота в состояние "Остановить запись"
    """

    logger.info('Received the stop_recording command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.stop_recording)


@router.message(Command(commands=['ping_obs']))
async def ping_obs(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "Проверить, доступна ли ОБС"
    """

    logger.info('Received the ping_obs command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.ping_obs)


@router.message(Command(commands=['ping_stream']))
async def ping_stream(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "Проверить состояние стрима на ОБС"
    """

    logger.info('Received the ping_stream command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.ping_stream)


@router.message(Command(commands=['ping_recording']))
async def ping_recording(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "Проверить состояние записи на ОБС"
    """

    logger.info('Received the ping_recording command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.ping_recording)


@router.message(Command(commands=['get_scenes']))
async def get_scenes(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "Вывести информацию о сценах в ОБС"
    """

    logger.info('Received the get_scenes command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.get_scenes)


@router.message(Command(commands=['set_scene']))
async def set_scene(message: Message, state: FSMContext):
    """
    Переводит бота в состояние "Выбрать ОБС"
    """

    logger.info('Received the get_scenes command')
    await show_obs_keyboard(message, state)
    await state.set_state(Form.select_obs_set_scene)


@router.message(Form.add_obs)
async def process_add_obs(message: Message, state: FSMContext) -> None:
    """
    Принимает имя, ip, порт и пароль нового OBS, проверяет на корректность
    и регистрирует его в БД
    """
    logger.info('Set to add_obs state')

    # проверяем, что данные ввели в нужной форме (через абзац)
    try:
        name, ip, port, password = message.text.split('\n')
    except Exception as err:
        logger.info('Incorrect info, asked for data again')
        logger.debug(str(err))
        await message.answer("Пожалуйста, введите данные корректно, каждое поле с новой строки.", reply_markup=ikb_cancel)
        await state.set_state(Form.add_obs)
        return

    name = name.strip()
    ip = ip.strip()
    port = port.strip()
    password = password.strip()
    logger.info('Received obs_name, ip, port and password')

    # проверяем на корректность данных:
    if ip.count('.') != 3 or not ip.replace('.', '').isdigit() or not port.isdigit():
        logger.info('Data is incorrect')
        await message.answer("Пожалуйста, введите данные корректно", reply_markup=ikb_cancel)
        await state.set_state(Form.add_obs)
    else:
        logger.info('Data seems to be correct')
        obs_id = str(uuid.uuid4())  # id obs в базе данных

        # Удаляем сообщение с данными
        await message.delete()
        logger.info(f'Deleted the message')

        user_id = message.from_user.id
        body = {"user_id": user_id,
                # "obs_id": obs_id,
                "obs_name": name, "ip": ip, "port": port, "password": password}
        url = 'http://127.0.0.1:8000/add_obs'
        response = requests.post(url, data=json.dumps(body))
        logger.info(f'Sent user_id, obs_name, ip, port and password and received {str(response.status_code)}')
        logger.info(f'Sent user_id and received {str(response.content)}')

        if response.status_code == 200:
            await message.answer('Стенд с OBS успешно добавлен.')
        elif response.status_code == 409:
            await message.answer(
                'Стенд с таким именем или сочетанием ip и порта уже существует. Пожалуйста, проверьте, что ввели верный ip и попробуйте снова.')
        else:
            await message.reply("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs
Вы также можете нажать /start и попробовать выполнить команду снова.""")
        await state.clear()


@router.message(Form.select_obs_edit_obs)
async def process_select_obs_edit_obs(message: Message, state: FSMContext) -> None:
    await state.update_data(obs_name=message.text)

    await show_fields_keyboard(message, state)
    await state.set_state(Form.select_field)


@router.message(Form.select_field)
async def process_select_field(message: Message, state: FSMContext) -> None:
    field = message.text
    await state.update_data(field=field)

    new = 'новое' if (field == 'Название') else 'новый'     # для корректного вывода сообщения на русском
    await message.answer(f'Введите {new} {field.lower()}:', reply_markup=ikb_cancel)

    await state.set_state(Form.get_new_value)


@router.message(Form.get_new_value)
async def process_get_new_value(message: Message, state: FSMContext) -> None:
    new_value = message.text
    user_id = message.from_user.id
    user_data = await state.get_data()
    field = user_data['field']
    obs_name = user_data['obs_name']

    if field == 'Пароль':
        await message.delete()
        logger.info(f'Deleted the message')

    if field in fields_db:
        field = fields_db[field]
    else:
        await message.answer('Такого поля у OBS нет. Пожалуйста, проверьте правильность написания и попробуйте заново.',
                             reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

    body = {"user_id": user_id, "obs_name": obs_name, "field_to_change": field, "new_value": new_value}
    url = 'http://127.0.0.1:8000/edit_obs'
    response = requests.post(url, data=json.dumps(body))
    logger.info(f'Sent user_id obs_name, field and value and got {str(response.status_code)}')
    logger.info(f'Sent user_id and received {str(response.content)}')

    if response.status_code == 200:
        await message.answer('Изменения совершены успешно', reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 404:
        await message.answer('ОБС с таким именем не найден. Пожалуйста, проверьте корректность написания', reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer(
            'Произошла ошибка. Проверьте, правильно ли вы ввели название стенда. Вы также можете нажать /start и попробовать выполнить команду снова.',
            reply_markup=types.ReplyKeyboardRemove())

    await state.clear()


@router.message(Form.delete_obs)
async def process_delete_obs(message: Message, state: FSMContext) -> None:
    """
    Принимает имя стенда ОБС и просит подтвердить удаление
    """

    obs_name = message.text
    await state.update_data(obs_name=obs_name)
    logger.info('Received OBS name')
    purpose = 'удалить стенд '+obs_name
    await show_yes_no_keyboard(message, state, purpose)
    await state.set_state(Form.delete_obs_confirmed)


@router.message(Form.delete_obs_confirmed)
async def process_delete_obs_confirmed(message: Message, state: FSMContext) -> None:
    """
    Принимает подтверждение и удаляет ОБС, если у пользователя он есть в списке доступных
    """

    if message.text.lower() == 'да':

        user_data = await state.get_data()
        obs_name = user_data['obs_name']

        user_id = message.from_user.id
        logger.info('Received obs_name')
        body = {"user_id": user_id, "obs_name": obs_name}
        url = 'http://127.0.0.1:8000/delete_obs'
        response = requests.delete(url, data=json.dumps(body))
        logger.info('sent'+str(body))
        logger.info(f'Sent user_id and obs_name {obs_name} and received {str(response.status_code)}')
        logger.info(response.content)

        if response.status_code == 200:
            await message.answer('Стенд с OBS успешно удалён', reply_markup=types.ReplyKeyboardRemove())
        elif response.status_code == 404:
            await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                                 reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer(
                'Произошла ошибка. Проверьте, правильно ли вы ввели название стенда. Вы также можете нажать /start и попробовать выполнить команду снова.',
                reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer('OBS не удалён.', reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@router.message(Form.select_obs_start_stream)
async def process_select_obs_start_stream(message: Message, state: FSMContext) -> None:
    """
    Принимает имя стенда ОБС и ключ трансляции и начинает стрим
    """
    obs_name = message.text
    await state.update_data(obs_name=obs_name)

    await message.answer("""Укажите ключ трансляции и YouTube сервер (поле URL трансляции). Оба поля нужно ввести с новой строки
Например:""", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("""vktx-qgw5-30vy-jm0z-fqq1
rtmp://a.rtmp.youtube.com/live2""", reply_markup=ikb_cancel)
    await state.set_state(Form.select_server_key)


@router.message(Form.select_server_key)
async def process_select_server_key(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        key, youtube_server = message.text.split('\n')
        logger.info('Received server and key')
        user_id = message.from_user.id

        user_data = await state.get_data()
        obs_name = user_data['obs_name']

        body = {"user_id": user_id, "obs_name": obs_name, "key": key, "youtube_server": youtube_server}
        url = 'http://127.0.0.1:8000/start_stream'
        response = requests.post(url, data=json.dumps(body))
        logger.info(f'Sent user_id, obs_name and key and received {str(response.status_code)}')
        logger.info(f'Sent user_id and received {str(response.content)}')

        if response.status_code == 200:
            await message.answer('Стрим успешно запущен.')
            await group_notifications.send_group_notifications(bot, message.from_user, user_data['obs_name'],
                                                               'start_stream')
        elif response.status_code == 404:
            await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.')
        elif response.status_code == 409:
            if 'in use' in str(response.content):
                await message.answer(
                    "Данный стенд сейчас занят. Вы можете выбрать другой. Список доступных стендов можете посмотреть командой /check_obs")
            elif 'unavailable' in str(response.content):
                await message.answer(
                    """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs
Вы также можете нажать /start и попробовать выполнить команду снова.""")

        await message.delete()
        logger.info(f'Deleted the message')

    except Exception as err:
        logger.info('Incorrect info, asked for data again')
        logger.debug(err)
        await message.answer("Пожалуйста, введите данные корректно, каждое поле с новой строки.", reply_markup=ikb_cancel)
        await state.set_state(Form.select_server_key)

    await state.clear()


@router.message(Form.start_recording)
async def process_start_recording(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Принимает имя стенда ОБС и ключ трансляции и начинает стрим
    """

    name = message.text
    logger.info('Received OBS name')
    user_id = message.from_user.id
    body = {"user_id": user_id, "obs_name": name}
    url = 'http://127.0.0.1:8000/start_recording'
    response = requests.post(url, data=json.dumps(body))
    logger.info(f'Sent user_id, obs_name and received {str(response.status_code)}')
    logger.info(f'Sent user_id and received {str(response.content)}')

    if response.status_code == 200:
        await message.answer('Запись успешно запущена.', reply_markup=types.ReplyKeyboardRemove())
        await group_notifications.send_group_notifications(bot, message.from_user, name, 'start_recording')
    elif response.status_code == 404:
        await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                             reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 409:
        if 'in use' in str(response.content):
            await message.answer(
                "Данный стенд сейчас занят. Вы можете выбрать другой. Список доступных стендов можете посмотреть командой /check_obs",
                reply_markup=types.ReplyKeyboardRemove())
        elif 'unavailable' in str(response.content):
            await message.answer(
                """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())

    await state.clear()


@router.message(Form.stop_recording)
async def process_stop_recording(message: Message, state: FSMContext) -> None:
    """
    Принимает имя стенда ОБС и ключ трансляции и начинает стрим
    """

    obs_name = message.text
    await state.update_data(obs_name=obs_name)
    logger.info('Received OBS name')
    purpose = 'остановить запись на стенде '+obs_name
    await show_yes_no_keyboard(message, state, purpose)
    await state.set_state(Form.stop_recording_confirmed)


@router.message(Form.stop_recording_confirmed)
async def process_stop_recording_confirmed(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.text.lower() == 'да':
        user_id = message.from_user.id
        user_data = await state.get_data()
        obs_name = user_data['obs_name']

        body = {"user_id": user_id, "obs_name": obs_name}
        url = 'http://127.0.0.1:8000/stop_recording'
        response = requests.post(url, data=json.dumps(body))
        logger.info(f'Sent user_id, obs_name and received {str(response.status_code)}')

        if response.status_code == 200:
            await message.answer('Запись успешно остановлена.', reply_markup=types.ReplyKeyboardRemove())
            await group_notifications.send_group_notifications(bot, message.from_user, obs_name, 'stop_recording')
        elif response.status_code == 404:
            await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                                 reply_markup=types.ReplyKeyboardRemove())
        elif response.status_code == 409:
            if 'not running' in str(response.content):
                await message.answer(
                    "На этом OBS запись не идёт", reply_markup=types.ReplyKeyboardRemove())
            elif 'unavailable' in str(response.content):
                await message.answer(
                    """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Запись не остановлена.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@router.message(Form.select_name)  # для планирования
async def process_select_name(message: Message, state: FSMContext) -> None:
    """
    Принимает ключ трансляции для планирования стрима, переключает бота в состояние "Выбор ОБС для стрима"
    """

    name = message.text
    await state.update_data(name=name)
    logger.info('Received the name, asked to select key')
    await state.set_state(Form.select_key)
    await message.answer('Теперь введите ключ трансляции', reply_markup=ikb_cancel)


@router.message(Form.select_key)  # для планирования
async def process_select_key(message: Message, state: FSMContext) -> None:
    """
    Принимает ключ трансляции для планирования стрима, переключает бота в состояние "Выбор ОБС для стрима"
    """

    key = message.text
    await state.update_data(key=key)

    await message.delete()
    logger.info(f'Deleted the message')

    logger.info('Received the key, asked to select youtube_server')
    await state.set_state(Form.select_youtube_server)
    await message.answer('Теперь введите сервер YouTube (вкладка "URL трансляции")', reply_markup=ikb_cancel)


@router.message(Form.select_youtube_server)  # для планирования
async def process_select_youtube_server(message: Message, state: FSMContext) -> None:
    """
    Принимает URL трансляции для планирования стрима, переключает бота в состояние "Выбор ОБС для стрима"
    """

    youtube_server = message.text
    if 'rtmp://' not in youtube_server or 'youtube.com' not in youtube_server:
        await message.answer('Пожалуйста, введите корректный URL. Попробуйте ещё раз.')
        await state.set_state(Form.select_youtube_server)
    else:
        await state.update_data(youtube_server=youtube_server)
        logger.info('Received the youtube server, asked to select obs')
        await show_obs_keyboard(message, state)
        await state.set_state(Form.select_obs_plan_stream)


@router.message(Form.select_obs_plan_stream)  # для планирования
async def process_select_obs_plan_stream(message: Message, state: FSMContext) -> None:
    """
    Принимает название ОБС для планирования стрима и планирует стрим, если всё ок
    """

    name_obs = message.text
    logger.info('Received name_obs')
    user_id = message.from_user.id

    body = {"user_id": user_id, "obs_name": name_obs}

    # запрашиваем в БД информацию об этом стенде:
    url = "http://127.0.0.1:8000/get_obs_info"
    response = requests.get(url, data=json.dumps(body))
    if response.status_code == 200:  # проверяем успешность запроса
        response_data = response.json()  # получаем данные в формате JSON

        # сохраняем полученные из БД данные
        await state.update_data(ip=response_data["ip"])
        await state.update_data(port=response_data["port"])
        await state.update_data(password=response_data["password"])

        await message.answer("""Введите дату и время начала и окончания стрима в формате MM/ДД/ГГГГ ЧЧ:ММ:СС.
Данные нужно вводить с новой строки -- на первой строке начало, на второй окончание.
Например:""", reply_markup=types.ReplyKeyboardRemove())
        await message.answer("""05/19/2023 18:53:00
05/19/2023 18:59:00""", reply_markup=ikb_cancel)
        await state.set_state(Form.select_date)

    elif response.status_code == 404:
        await message.answer('Стенд OBS с таким именем не найден. Попробуйте ещё раз.',
                             reply_markup=types.ReplyKeyboardRemove())
        await show_obs_keyboard(message, state)
        await state.set_state(Form.select_obs_plan_stream)
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())


@router.message(Form.select_date)  # для планирования
async def process_select_date(message: Message, state: FSMContext) -> None:
    """
    Принимает даты начала и окончания для планирования стрима, если всё ок -- переключает
    бота в состояние "Выбрать ключ стрима"
    """

    try:
        date1, date2 = message.text.split('\n')
        logger.info('Received two strings as dates')
        # преобразуем теперь даты в нужный формат, если они введены верно
        date1 = datetime.datetime.strptime(date1, "%m/%d/%Y %H:%M:%S")
        date2 = datetime.datetime.strptime(date2, "%m/%d/%Y %H:%M:%S")
        logger.info('Input strings are correct dates')
        if date1 < date2:
            # если даты идут в нужном порядке, сохраняем их
            await state.update_data(date1=str(date1))
            await state.update_data(date2=str(date2))

            logger.info('date1<date2, sending data to calendar')
            await send_data_to_calendar(message, state)
        else:
            logger.info('Error: date1>=date2')
            await message.answer('Пожалуйста, введите корректные данные о датах: сперва начало, затем конец.',
                                 reply_markup=ikb_cancel)
            await state.set_state(Form.select_date)
    except Exception as err:
        logger.info('Incorrect input, asked for data again')
        logger.debug(err)
        await message.answer("Пожалуйста, введите данные корректно в формате ММ/ДД/ГГГГ ЧЧ:ММ:СС.",
                             reply_markup=ikb_cancel)
        await state.set_state(Form.select_date)


@router.message(Form.select_name_plan_recording)  # для планирования
async def process_select_name_plan_rec(message: Message, state: FSMContext) -> None:
    """
    Принимает ключ трансляции для планирования стрима, переключает бота в состояние "Выбор ОБС для стрима"
    """

    name = message.text
    await state.update_data(name=name)
    logger.info('Received the name, asked to select key')
    await state.set_state(Form.select_obs_plan_recording)
    await message.answer('Теперь введите ключ трансляции', reply_markup=ikb_cancel)


@router.message(Form.select_obs_plan_recording)  # для планирования
async def process_select_obs_plan_rec(message: Message, state: FSMContext) -> None:
    """
    Принимает название ОБС для планирования стрима и планирует стрим, если всё ок
    """

    name_obs = message.text
    logger.info('Received name_obs')
    user_id = message.from_user.id

    body = {"user_id": user_id, "obs_name": name_obs}

    # запрашиваем в БД информацию об этом стенде:
    url = "http://127.0.0.1:8000/get_obs_info"
    response = requests.get(url, data=json.dumps(body))
    if response.status_code == 200:  # проверяем успешность запроса
        response_data = response.json()  # получаем данные в формате JSON

        # сохраняем полученные из БД данные
        await state.update_data(ip=response_data["ip"])
        await state.update_data(port=response_data["port"])
        await state.update_data(password=response_data["password"])

        await message.answer("""Введите дату и время начала и окончания стрима в формате MM/ДД/ГГГГ ЧЧ:ММ:СС.
Данные нужно вводить с новой строки -- на первой строке начало, на второй окончание.
Например:""", reply_markup=types.ReplyKeyboardRemove())
        await message.answer("""05/19/2023 18:53:00
05/19/2023 18:59:00""", reply_markup=ikb_cancel)
        await state.set_state(Form.select_date_plan_recording)

    elif response.status_code == 404:
        await message.answer('Стенд OBS с таким именем не найден. Попробуйте ещё раз.',
                             reply_markup=types.ReplyKeyboardRemove())
        await show_obs_keyboard(message, state)
        await state.set_state(Form.select_obs_plan_recording)
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())


@router.message(Form.select_date_plan_recording)  # для планирования
async def process_select_date(message: Message, state: FSMContext) -> None:
    """
    Принимает даты начала и окончания для планирования стрима, если всё ок -- переключает
    бота в состояние "Выбрать ключ стрима"
    """

    try:
        date1, date2 = message.text.split('\n')
        logger.info('Received two strings as dates')
        # преобразуем теперь даты в нужный формат, если они введены верно
        date1 = datetime.datetime.strptime(date1, "%m/%d/%Y %H:%M:%S")
        date2 = datetime.datetime.strptime(date2, "%m/%d/%Y %H:%M:%S")
        logger.info('Input strings are correct dates')
        if date1 < date2:
            # если даты идут в нужном порядке, сохраняем их
            await state.update_data(date1=str(date1))
            await state.update_data(date2=str(date2))

            logger.info('date1<date2, sending data to calendar')
            await send_data_to_calendar(message, state)  # TODO: another function
        else:
            logger.info('Error: date1>=date2')
            await message.answer('Пожалуйста, введите корректные данные о датах: сперва начало, затем конец.',
                                 reply_markup=ikb_cancel)
            await state.set_state(Form.select_date_plan_recording)
    except Exception as err:
        logger.info('Incorrect input, asked for data again')
        logger.debug(err)
        await message.answer("Пожалуйста, введите данные корректно в формате ММ/ДД/ГГГГ ЧЧ:ММ:СС.",
                             reply_markup=ikb_cancel)
        await state.set_state(Form.select_date_plan_recording)


@router.message(Form.stop_stream)
async def process_stop_stream(message: Message, state: FSMContext) -> None:
    """
    Принимает имя стенда ОБС и просит подтвердить остановку стрима
    """

    obs_name = message.text
    await state.update_data(obs_name=obs_name)
    logger.info('Received OBS name')
    purpose = 'остановить стрим на стенде '+obs_name
    await show_yes_no_keyboard(message, state, purpose)
    await state.set_state(Form.stop_stream_confirmed)


@router.message(Form.stop_stream_confirmed)
async def process_stop_stream_confirmed(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Принимает ответ "да/нет", останавливает стрим, если "да"
    """
    if message.text.lower() == 'да':

        user_data = await state.get_data()
        obs_name = user_data['obs_name']

        user_id = message.from_user.id

        body = {"user_id": user_id, "obs_name": obs_name}
        url = 'http://127.0.0.1:8000/stop_stream'
        response = requests.post(url, data=json.dumps(body))
        logger.info(f'Sent user_id and obs_name and received {str(response.status_code)}')
        logger.info(f'Sent user_id and received {str(response.content)}')

        if response.status_code == 200:
            await message.answer('Стрим успешно остановлен.', reply_markup=types.ReplyKeyboardRemove())
            await group_notifications.send_group_notifications(bot, message.from_user, obs_name, 'stop_stream')
        elif response.status_code == 404:
            await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                                 reply_markup=types.ReplyKeyboardRemove())
        elif response.status_code == 409:
            if 'not running' in str(response.content):
                await message.answer(
                    "На данном OBS стрим не идёт", reply_markup=types.ReplyKeyboardRemove())
            elif 'unavailable' in str(response.content):
                await message.answer(
                    """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
    Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())

        else:
            await message.answer("""Произошла ошибка.
    Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs
    Вы также можете нажать /start и попробовать выполнить команду снова.""")

    else:
        await message.answer('Стрим не остановлен', reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@router.message(Form.get_scenes)
async def process_get_scenes(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    name_obs = message.text  # берём имя с нажатой кнопки
    logger.info(f'Received obs name {name_obs}')

    # теперь смотрим, какие сцены есть у ОБС с таким именем
    body = {"user_id": user_id, "obs_name": name_obs}
    url = 'http://127.0.0.1:8000/get_scenes'
    response = requests.get(url, data=json.dumps(body))
    logger.info(f'Sent user_id and obs_name and received {str(response.status_code)}')
    logger.info(f'{str(response.content)}')

    if response.status_code == 200:
        data = response.json()  # получаем данные в формате JSON
        if len(data["all"]) == 0:
            await message.answer('На данном OBS ещё нет сцен.', reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer(
                f"""Сейчас в OBS есть следующие сцены: {str(data["all"])[1:-1]}.
Текущая сцена в Program: {data["current"]}.""", reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 409:
        await message.answer(
            """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 404:
        await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                             reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs.
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())

        await state.clear()


@router.message(Form.select_obs_set_scene)
async def process_select_obs_set_scene(message: Message, state: FSMContext) -> None:
    """
    Выбирает имя с ОБС и показывает доступные сцены
    """
    obs_name = message.text
    await state.update_data(obs_name=obs_name)

    await show_scenes_keyboard(obs_name, message, state)
    await state.set_state(Form.select_scene)
    logger.info('Received obs_name, asked to select a scene')


@router.message(Form.select_scene)
async def process_select_scene(message: Message, state: FSMContext) -> None:
    """
    Выбирает сцену и устанавливает её
    """
    user_id = message.from_user.id
    scene_name = message.text

    user_data = await state.get_data()
    obs_name = user_data['obs_name']

    body = {"user_id": user_id, "obs_name": obs_name, "scene_name": scene_name}
    url = 'http://127.0.0.1:8000/set_scene'
    response = requests.get(url, data=json.dumps(body))
    logger.info(f'Sent , scene_name and obs_name and received {str(response.status_code)}')
    logger.info(f'{str(response.content)}')

    if response.status_code == 200:
        await message.answer(f'Установлена текущая сцена {scene_name}', reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 409:
        await message.answer(
            """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 404:
        await message.answer('Сцена с таким именем не найдена. Пожалуйста, проверьте правильность написания.',
                             reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs.
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())

        await state.clear()


@router.message(Form.ping_obs)
async def process_ping_obs(message: Message, state: FSMContext) -> None:
    """
    Проверяет, доступна ли ОБС с таким именем
    """

    user_id = message.from_user.id
    name_obs = message.text
    logger.info('Received obs_name')

    body = {"user_id": user_id, "obs_name": name_obs}
    url = 'http://127.0.0.1:8000/ping_obs'
    response = requests.get(url, data=json.dumps(body))
    logger.info(f'Sent user_id and obs_name and received {str(response.status_code)}')
    logger.info(f'Sent user_id and received {str(response.content)}')

    if response.status_code == 200:
        await message.answer('Стенд доступен.', reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 404:
        await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                             reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 451:
        await message.answer('Сейчас данный стенд недоступен.', reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs.
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())

        await state.clear()


@router.message(Form.ping_stream)
async def process_ping_stream(message: Message, state: FSMContext) -> None:
    """
    Проверяет, запущен ли стрим на ОБС с таким именем,
    и как у него дела
    """

    user_id = message.from_user.id
    name_obs = message.text
    logger.info('Received obs_name')

    body = {"user_id": user_id, "obs_name": name_obs}
    url = 'http://127.0.0.1:8000/ping_stream'
    response = requests.get(url, data=json.dumps(body))
    logger.info(f'Sent user_id and obs_name and received {str(response.status_code)}')
    logger.info(f'Sent user_id and received {str(response.content)}')

    if response.status_code == 200:
        data = response.json()  # получаем данные в формате JSON
        stream_time = data["stream_time"]
        await message.answer(f'На этом стенде с OBS идёт трансляция на протяжении {stream_time}',
                             reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 404:
        await message.answer('Стенд с таким именем не найден. Пожалуйста, проверьте правильность написания.',
                             reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 451:
        await message.answer('На выбранном стенде с OBS стрим не идёт.', reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 409:
        await message.answer(
            """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs.
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())

    await state.clear()


@router.message(Form.ping_recording)
async def process_ping_recording(message: Message, state: FSMContext) -> None:
    """
    Проверяет, запущена ли запись на ОБС с таким именем,
    и как у него дела
    """

    user_id = message.from_user.id
    name_obs = message.text
    logger.info('Received obs_name')

    body = {"user_id": user_id, "obs_name": name_obs}
    url = 'http://127.0.0.1:8000/ping_recording'
    response = requests.get(url, data=json.dumps(body))
    logger.info(f'Sent user_id and obs_name and received {str(response.status_code)}')
    logger.info(f'Sent user_id and received {str(response.content)}')

    if response.status_code == 200:
        data = response.json()  # получаем данные в формате JSON
        recording_time = data["recording_time"]
        await message.answer(f'На этом стенде с OBS идёт запись на протяжении {recording_time}',
                             reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 451:
        await message.answer('На выбранном стенде с OBS запись не идёт.', reply_markup=types.ReplyKeyboardRemove())
    elif response.status_code == 409:
        await message.answer(
            """Данный стенд с OBS сейчас недоступен. Вы можете попробовать выбрать другой стенд с OBS из доступных.
Их список вы можете посмотреть командой /check_obs.""",  reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("""Произошла ошибка.
Вы можете попробовать выбрать другой стенд с OBS из доступных. Их список вы можете посмотреть командой /check_obs.
Вы также можете нажать /start и попробовать выполнить команду снова.""", reply_markup=types.ReplyKeyboardRemove())

    await state.clear()
