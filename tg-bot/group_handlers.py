from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ChatMemberUpdated, ChatMemberLeft, CallbackQuery, ReplyKeyboardRemove, User, \
    ForceReply
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, LEAVE_TRANSITION, Command, PROMOTED_TRANSITION, \
    ADMINISTRATOR, MEMBER
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
import requests
import json
from loguru import logger
from filters import ChatTypeFilter

router = Router()
router.message.filter(ChatTypeFilter(chat_type=["group", "supergroup"]))

fields_db = {"Название": "obs_name", "IP": "ip", "Порт": "port", "Пароль": "password"}


class GroupForm(StatesGroup):
    add_obs_group = State()
    delete_obs_group = State()
    select_obs_edit_obs = State()
    select_field = State()
    get_new_value = State()


def get_username_or_id(user: User) -> str:
    """Для идентификации пользователя в информационных сообщениях по username или id в случае отсутствия username"""
    user_str = f'@{user.username}' if user.username else str(user.id)
    return user_str


async def check_admin(bot: Bot, chat_id, user_id) -> bool:
    """Проверка на админа/создателя группы"""
    chat_member = await bot.get_chat_member(chat_id=chat_id,
                                            user_id=user_id)
    return True if chat_member.status in ['creator', 'administrator'] else False


# @router.message((F.text.split('@')[0] == '/add_obs'))
@router.message(Command('add_obs', ignore_mention=True))
async def add_obs(message: Message, state: FSMContext, bot: Bot):
    """Добавление obs группы"""
    if await check_admin(bot, message.chat.id, message.from_user.id):
        response = requests.get('http://127.0.0.1:8000/check_obs',
                                data=json.dumps({"user_id": message.from_user.id, "need_availability": False}))
        if response.status_code == 200:
            data = response.json()
            user_obs_names = [obs_name for obs_name in data]  # нам нужны только названия ОБС, они являются ключами
            if len(user_obs_names) == 0:
                await message.answer(
                    'У вас ещё нет персональных стендов с OBS.'
                    'Вы можете добавить их командой /add_obs в личном чате с ботом.')
                logger.info(f'There are no stands for user {message.from_user.id}')
            else:
                body = {"group_id": message.chat.id}  # Убираем те обс, которые уже есть в группе
                url = 'http://127.0.0.1:8000/check_group_obs'
                response = requests.get(url, data=json.dumps(body))
                if response.status_code == 200:
                    data = response.json()
                    group_obs_names = [obs_name for obs_name in data]

                    obs_names = []
                    for i in user_obs_names:
                        if i not in group_obs_names:
                            obs_names.append(i)
                    if len(obs_names) == 0:
                        await message.answer(
                            'Все ваши OBS уже добавлены в эту группу.')
                        logger.info(
                            f'All personal obs of user {message.from_user.id} are already added to group {message.chat.id} ')
                    else:
                        # Добавляем их на кнопки
                        ibuttons = []
                        checked = []
                        for i in range(len(obs_names)):
                            ibuttons.append([InlineKeyboardButton(text=obs_names[i],
                                                                  callback_data=f'group_add_check_{i}')])
                            checked.append(False)
                        ibuttons.append(
                            [InlineKeyboardButton(text='ДОБАВИТЬ ВЫБРАННЫЕ', callback_data='group_add_confirm')]
                        )
                        ibuttons.append(
                            [InlineKeyboardButton(text='ОТМЕНА', callback_data='cancel')]
                        )
                        ikb_temp = InlineKeyboardMarkup(inline_keyboard=ibuttons)
                        await state.set_state(GroupForm.add_obs_group)
                        await state.update_data(obs_names=obs_names, checked=checked)

                        await message.answer('Выберите стенд с OBS:', reply_markup=ikb_temp)
                        logger.info('Formed a keyboard, asked to choose obs')
                else:
                    await message.answer('Ошибка при получении obs группы')

        else:
            logger.debug(f'Error with user id "{message.from_user.id}"')
            await message.answer("""Произошла ошибка.""")
    else:
        await message.answer('Только администратор может менять obs группы!')


@router.callback_query(F.data.startswith('cancel'))
async def name(call: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await call.message.delete()
    except:
        pass
    await state.clear()
    await call.message.answer('Действие отменено.')


@router.callback_query(F.data.startswith('group_add_check_'))
async def name(call: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_admin(bot, call.message.chat.id, call.from_user.id):
        checked_obs_index = int(call.data[16:])
        data = await state.get_data()
        checked = data['checked']
        checked[checked_obs_index] = not checked[checked_obs_index]
        await state.update_data(checked=checked)
        ibuttons = []
        for i in range(len(data['obs_names'])):
            text = '✅ {name}' if checked[i] else '{name}'
            ibuttons.append([InlineKeyboardButton(text=text.format(name=data['obs_names'][i]),
                                                 callback_data=f'group_add_check_{i}')])
        ibuttons.append([InlineKeyboardButton(text='ДОБАВИТЬ ВЫБРАННЫЕ',
                                              callback_data='group_add_confirm')]
                        )
        ibuttons.append(
            [InlineKeyboardButton(text='ОТМЕНА', callback_data='cancel')]
        )
        ikb_temp = InlineKeyboardMarkup(inline_keyboard=ibuttons)
        await call.message.edit_reply_markup(reply_markup=ikb_temp)
    else:
        await call.answer('Только администратор может выбирать obs', show_alert=True)


@router.callback_query(F.data == 'group_add_confirm')
async def name(call: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_admin(bot, call.message.chat.id, call.from_user.id):
        try:
            await call.message.delete()
        except:
            pass
        data = await state.get_data()
        await state.clear()
        obs_to_add = []
        for i in range(len(data['obs_names'])):
            if data['checked'][i]:
                obs_to_add.append(data['obs_names'][i])
        if len(obs_to_add) != 0:
            body = {"group_id": call.message.chat.id, "admin_id": call.from_user.id, "obs_names": obs_to_add}
            url = 'http://127.0.0.1:8000/add_group_obs'
            response = requests.post(url, data=json.dumps(body))

            if response.status_code == 200:
                text = f'Добавлены:\n'
                response_decoded = json.loads(response.content.decode('utf-8'))
                for obs_name in response_decoded['added']:
                    text += f'{obs_name}\n'
                if len(response_decoded['missed']) != 0:
                    text += f'\n\nНе удалось добавить:\n'
                    for obs_name in response_decoded['missed']:
                        text += f'{obs_name}\n'
                await call.message.answer(text)

                logger.info(f'Added {len(obs_to_add)} to froup {call.message.chat.id}')
            elif response.status_code == 409:
                await call.message.answer(
                    'Стенд с таким именем или сочетанием ip и порта уже существует. Пожалуйста, проверьте, что ввели верный ip и попробуйте снова.')
            else:
                await call.message.answer('Произошла ошибка.')
        else:
            await call.message.answer('Не было добавлено ни одной obs')
    else:
        await call.answer('Только администратор может выбирать obs', show_alert=True)


@router.message(Command('check_obs', ignore_mention=True))
async def add_obs(message: Message, state: FSMContext, bot: Bot):
    """Показать obs группы"""
    body = {"group_id": message.chat.id}
    url = 'http://127.0.0.1:8000/check_group_obs'
    response = requests.get(url, data=json.dumps(body))
    if response.status_code == 200:
        if len(response.json()) == 0:
            await message.answer('К этой группе ещё не привязаны OBS. Чтобы добавить OBS, админ должен ввести команду /add_obs в группе.')
        else:
            text = 'OBS группы:\n'
            for obs_name, obs_data in response.json().items():
                # print(obs_name, obs_data)
                text += f'{obs_name}\nip: {obs_data["ip"]}\nпорт: {obs_data["port"]}\n\n'
            await message.answer(text)
    else:
        await message.answer('Ошибка, не удалось получить OBS группы.')


@router.message(Command('delete_obs', ignore_mention=True))
async def delete_obs(message: Message, state: FSMContext, bot: Bot):
    """Удаление obs группы"""
    if await check_admin(bot, message.chat.id, message.from_user.id):
        response = requests.get('http://127.0.0.1:8000/check_group_obs',
                                data=json.dumps({"group_id": message.chat.id}))
        if response.status_code == 200:
            data = response.json()
            obs_names = [obs_name for obs_name in data]  # нам нужны только названия ОБС, они являются ключами

            # Добавляем их на кнопки
            if len(obs_names) == 0:
                await message.answer(
                    'У группы нет стендов с OBS. Вы можете добавить их командой /add_obs в этом чате.')
                logger.info(f'There are no stands for group {message.chat.id}')
            else:
                ibuttons = []
                checked = []
                for i in range(len(obs_names)):
                    ibuttons.append([InlineKeyboardButton(text=obs_names[i], callback_data=f'group_delete_check_{i}')])
                    checked.append(False)
                ibuttons.append([InlineKeyboardButton(text='УДАЛИТЬ ВЫБРАННЫЕ', callback_data='group_delete_confirm')])
                ibuttons.append(
                    [InlineKeyboardButton(text='ОТМЕНА', callback_data='cancel')]
                )
                ikb_temp = InlineKeyboardMarkup(inline_keyboard=ibuttons)
                await state.set_state(GroupForm.delete_obs_group)
                await state.update_data(obs_names=obs_names, checked=checked)

                await message.answer('Выберите стенд с OBS:', reply_markup=ikb_temp)
                logger.info('Formed a keyboard, asked to choose obs')
        else:
            logger.debug(f'Error with user id "{message.from_user.id}"')
            await message.answer("""Произошла ошибка получения OBS группы.""")
    else:
        await message.answer('Только администратор может менять obs группы!')


@router.callback_query(F.data.startswith('group_delete_check_'))
async def name(call: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_admin(bot, call.message.chat.id, call.from_user.id):
        checked_obs_index = int(call.data[19:])
        data = await state.get_data()
        checked = data['checked']
        checked[checked_obs_index] = not checked[checked_obs_index]
        await state.update_data(checked=checked)
        ibuttons = []
        for i in range(len(data['obs_names'])):
            text = '❌ {name}' if checked[i] else '{name}'
            ibuttons.append([InlineKeyboardButton(text=text.format(name=data['obs_names'][i]),
                                                  callback_data=f'group_delete_check_{i}')])
        ibuttons.append([InlineKeyboardButton(text='УДАЛИТЬ ВЫБРАННЫЕ', callback_data='group_delete_confirm')])
        ibuttons.append(
            [InlineKeyboardButton(text='ОТМЕНА', callback_data='cancel')]
        )
        ikb_temp = InlineKeyboardMarkup(inline_keyboard=ibuttons)
        await call.message.edit_reply_markup(reply_markup=ikb_temp)
    else:
        await call.answer('Только администратор может выбирать obs', show_alert=True)


@router.callback_query(F.data == 'group_delete_confirm')
async def name(call: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_admin(bot, call.message.chat.id, call.from_user.id):
        try:
            await call.message.delete()
        except:
            pass
        data = await state.get_data()
        await state.clear()
        obs_to_delete = []
        for i in range(len(data['obs_names'])):
            if data['checked'][i]:
                obs_to_delete.append(data['obs_names'][i])
        if len(obs_to_delete) != 0:
            for i in obs_to_delete:
                body = {"group_id": call.message.chat.id, "obs_name": i}
                url = 'http://127.0.0.1:8000/delete_group_obs'
                response = requests.delete(url, data=json.dumps(body))
                if response.status_code == 200:
                    await call.message.answer(f'Удален {i}')
                elif response.status_code == 404:
                    await call.message.answer(
                        f'Стенд {i} не найден. Пожалуйста, проверьте правильность написания.')
                else:
                    await call.message.answer(f'Произошла ошибка при удалении {i}.')
        else:
            await call.message.answer('Не было удалено ни одной obs')
    else:
        await call.answer('Только администратор может выбирать obs', show_alert=True)


@router.message(Command('edit_obs', ignore_mention=True))
async def edit_obs(message: Message, state: FSMContext, bot: Bot):
    """Редактирование obs чата"""
    if await check_admin(bot, message.chat.id, message.from_user.id):
        logger.info('Received the edit_obs command in gtoup')
        user_id = message.from_user.id

        # получаем список OBS, чтобы добавить на кнопки

        body = {"group_id": message.chat.id}
        url = 'http://127.0.0.1:8000/check_group_obs'
        response = requests.get(url, data=json.dumps(body))
        if response.status_code == 200:
            data = response.json()
            obs_names = [obs_name for obs_name in data]  # нам нужны только названия ОБС, они являются ключами

            # Добавляем их на кнопки
            if len(obs_names) == 0:
                await message.answer(
                    'У вас ещё нет стендов с OBS. Вы можете добавить их командой /add_obs.')
                logger.info(f'There are no stands for group {message.chat.id}')
            else:
                # делаем массив из строчек по 3 кнопки в каждой
                buttons = [KeyboardButton(text=str(obs_names[i])) for i in range(len(obs_names))]
                buttons = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
                buttons.append([KeyboardButton(text='Отмена')])
                # Создаем клавиатуру
                keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, selective=True)

                # Отправляем сообщение с клавиатурой
                await message.reply('Выберите стенд с OBS:', reply_markup=keyboard)
                logger.info('Formed a keyboard, asked to choose obs')
                await state.set_state(GroupForm.select_obs_edit_obs)
        else:
            logger.debug(f'Error with group_id "{message.chat.id}"')
            await message.answer("""Произошла ошибка.
        Вы можете нажать /start и попробовать выполнить команду снова.""")
    else:
        await message.answer('Только администратор может изменять obs.')


@router.message(GroupForm.select_obs_edit_obs)
async def process_select_obs_edit_obs(message: Message, state: FSMContext, bot: Bot) -> None:
    if await check_admin(bot, message.chat.id, message.from_user.id):
        if message.text == 'Отмена':
            await state.clear()
            await message.answer('Отменено', reply_markup=ReplyKeyboardRemove())
        else:
            await state.update_data(obs_name=message.text)

            buttons = [[KeyboardButton(text='Название'), KeyboardButton(text='IP'), KeyboardButton(text='Порт'),
                        KeyboardButton(text='Пароль')]]
            buttons.append([KeyboardButton(text='Отмена')])
            keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, selective=True)
            await message.reply('Выберите параметр, который хотите изменить:', reply_markup=keyboard)
            logger.info('Formed a keyboard, asked to choose a field')
            await state.set_state(GroupForm.select_field)


@router.message(GroupForm.select_field)
async def process_select_field(message: Message, state: FSMContext, bot: Bot) -> None:
    if await check_admin(bot, message.chat.id, message.from_user.id):
        if message.text == 'Отмена':
            await state.clear()
            await message.answer('Отменено', reply_markup=ReplyKeyboardRemove())
        else:
            field = message.text
            await state.update_data(field=field)
            new = 'новое' if (field == 'Название') else 'новый'     # для корректного вывода сообщения на русском
            mes = await message.answer(f'Выбран параметр {field}', reply_markup=ReplyKeyboardRemove())
            await mes.delete()
            await message.answer(f'Введите {new} {field.lower()}:', reply_markup=ForceReply())
            logger.info('Asked for a new value, gonna switch to get_new_value state')
            await state.set_state(GroupForm.get_new_value)
    else:
        await message.answer('Только администратор может изменять OBS.')


@router.message(GroupForm.get_new_value)
async def process_get_new_value(message: Message, state: FSMContext, bot: Bot) -> None:
    logger.info('Switched to the get value state')
    if await check_admin(bot, message.chat.id, message.from_user.id):
        new_value = message.text
        user_data = await state.get_data()
        field = user_data['field']
        obs_name = user_data['obs_name']
        logger.info(f'Got new value for field {field}')

        if field == 'Пароль':
            await message.delete()
            logger.info(f'Deleted the message')

        if field in fields_db:
            field = fields_db[field]
        else:
            await message.answer('Такого поля у OBS нет. Пожалуйста, проверьте правильность написания и попробуйте заново.',
                                 reply_markup=ReplyKeyboardRemove())
            await state.clear()

        body = {"group_id": message.chat.id, "obs_name": obs_name, "field_to_change": field, "new_value": new_value}
        url = 'http://127.0.0.1:8000/edit_group_obs'
        response = requests.post(url, data=json.dumps(body))
        logger.info(f'Sent group_id obs_name, field and value and got {str(response.status_code)}')
        logger.info(f'Sent group_id and received {str(response.content)}')

        if response.status_code == 200:
            await message.answer('Изменения совершены успешно', reply_markup=ReplyKeyboardRemove())
        elif response.status_code == 404:
            await message.answer('ОБС с таким именем не найден. Пожалуйста, проверьте корректность написания', reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer(
                'Произошла ошибка. Проверьте, правильно ли вы ввели название стенда. Вы также можете нажать /start и попробовать выполнить команду снова.',
                reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer('Только администратор может изменять OBS.')

        await state.clear()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def chat_member(event: ChatMemberUpdated, bot: Bot):
    """Бота добавляют в чат"""
    if event.new_chat_member.user.id == bot.id:
        # await bot.send_message(event.chat.id, 'Информационное сообщение (Должен быть один участник и бот. СДЕЛАЙТЕ БОТА АДМИНОМ)')
        member_count = await bot.get_chat_member_count(event.chat.id)
        if member_count > 2:
            await bot.send_message(event.chat.id,
                                   f'В данный момент в чате {member_count - 2} участников помимо бота и админа. В новом чате должны быть только админ и бот. '
                                   f'Чтобы запустить бота в этом чате, удалите всех, кроме одного участника группы и бота, затем нажмите /start.')
        elif not await check_admin(bot, event.chat.id, event.new_chat_member.user.id):
            await bot.send_message(event.chat.id, f'На данный момент бот не является администратором.'
                                   'Чтобы запустить бота в этом чате, сделайте его админом, затем нажмите /start.')
        else:
            await bot.send_message(event.chat.id, 'Чтобы запустить бота в этом чате, нажмите /start.')
        #     body = {"group_id": event.chat.id}
        #     url = 'http://127.0.0.1:8000/add_group'
        #     response = requests.post(url, data=json.dumps(body))
        #     if response.status_code == 200:
        #         await bot.send_message(event.chat.id, 'Вижу группу. Теперь можно добавлять участников!')
        #
        #         await bot.send_message(event.chat.id, f'event.from_user.id {event.from_user.id}')
        #
        #         body = {"user_id": event.from_user.id}
        #         url = 'http://127.0.0.1:8000/register_user'  # регистрируем нового пользователя
        #         response = requests.post(url, data=json.dumps(body))
        #         logger.info(f'Sent user_id and received {str(response.status_code)}')
        #         logger.info(f'Sent user_id and received {str(response.content)}')
        #
        #         if response.status_code != 200:
        #             await bot.send_message(event.chat.id, 'Произошла ошибка. Пожалуйста, обратитесь к команде проекта СВТ-31.')
        #
        #         body = {"group_id": event.chat.id, "user_id": event.from_user.id, "is_admin": True}
        #         url = 'http://127.0.0.1:8000/add_group_member'
        #         response = requests.post(url, data=json.dumps(body))
        #         if response.status_code == 200:
        #             user_str = get_username_or_id(event.from_user)
        #             await bot.send_message(event.chat.id, f'Добавлен админ {user_str}')
        #         else:
        #             await bot.send_message(event.chat.id, 'Произошла ошибка добавления пользователя.')
        #     elif response.status_code == 409:
        #         await bot.send_message(event.chat.id, 'Группа уже добавлена.')
        #     else:
        #         await bot.send_message(event.chat.id, 'Произошла ошибка.')


@router.message(Command('start', ignore_mention=True))
async def chat_member(message: Message, state: FSMContext, bot: Bot):
    """Запрос на добавление группы"""
    member_count = await bot.get_chat_member_count(message.chat.id)
    if member_count > 2:
        await bot.send_message(message.chat.id,
                               f'В данный момент в чате {member_count - 2} участников помимо бота и админа. В новом чате должны быть только админ и бот. '
                               f'Чтобы запустить бота в этом чате, удалите всех, кроме одного участника группы и бота, затем нажмите /start.')
    elif not await check_admin(bot, message.chat.id, bot.id):
        await bot.send_message(message.chat.id, f'На данный момент бот не является администратором.'
                                              'Чтобы запустить бота в этом чате, сделайте его админом, затем нажмите /start.')
    else:
        body = {"group_id": message.chat.id}
        url = 'http://127.0.0.1:8000/add_group'
        response = requests.post(url, data=json.dumps(body))
        if response.status_code == 200:
            await bot.send_message(message.chat.id, 'Вижу группу. Теперь можно добавлять участников!')

            body = {"user_id": message.from_user.id}
            url = 'http://127.0.0.1:8000/register_user'  # регистрируем нового пользователя
            response = requests.post(url, data=json.dumps(body))
            logger.info(f'Sent user_id and received {str(response.status_code)}')
            logger.info(f'Sent user_id and received {str(response.content)}')

            if response.status_code != 200:
                user_str = get_username_or_id(message.from_user)
                await message.answer(f'Произошла ошибка при добавлении @{user_str}. Пожалуйста, обратитесь к команде проекта СВТ-31.')
            else:
                body = {"group_id": message.chat.id, "user_id": message.from_user.id, "is_admin": True}
                url = 'http://127.0.0.1:8000/add_group_member'
                user_response = requests.post(url, data=json.dumps(body))
                if user_response.status_code == 200:
                    user_str = get_username_or_id(message.from_user)
                    await bot.send_message(message.chat.id, f'Добавлен админ {user_str}')
                else:
                    await bot.send_message(message.chat.id, 'Произошла ошибка добавления пользователя.')
        elif response.status_code == 409:
            await bot.send_message(message.chat.id, 'Группа уже добавлена.')
        else:
            await bot.send_message(message.chat.id, 'Произошла ошибка.')


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=PROMOTED_TRANSITION))
async def chat_member(event: ChatMemberUpdated, bot: Bot):
    user_str = get_username_or_id(event.new_chat_member.user)
    body = {"group_id": event.chat.id, "user_id": event.from_user.id}
    url = 'http://127.0.0.1:8000/raise_to_admin'
    response = requests.post(url, data=json.dumps(body))
    if response.status_code == 200:
        await bot.send_message(event.chat.id, f'Пользователь {user_str} стал админом!')
    else:
        await bot.send_message(event.chat.id, f'Произошла ошибка повышения прав {user_str}.')


# @router.chat_member(ChatMemberUpdatedFilter(member_status_changed=(ADMINISTRATOR >> MEMBER)))
# async def chat_member(event: ChatMemberUpdated, bot: Bot):
#     # body = {"group_id": event.chat.id, "user_id": event.from_user.id, "is_admin": True}
#     # url = 'http://127.0.0.1:8000/add_group_member'
#     # response = requests.post(url, data=json.dumps(body))
#     # if response.status_code == 200:
#     #     await bot.send_message(event.chat.id, f'Добавлен админ @{event.from_user.username}')
#     # else:
#     #     await bot.send_message(event.chat.id, f'Произошла ошибка повышения прав @{event.from_user.username}.')
#     ### запрос на отянть права админа
#     user_str = get_username_or_id(event.new_chat_member.user)
#     await bot.send_message(event.chat.id, f'Пользователь {user_str} перестал быть админом.')


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def chat_member(event: ChatMemberUpdated, bot: Bot):
    """Пользователь присоединяется / пользователя добавляют в группу"""
    user_id = event.new_chat_member.user.id

    if user_id != bot.id:
        body = {"user_id": user_id}
        url = 'http://127.0.0.1:8000/register_user'  # регистрируем нового пользователя
        response = requests.post(url, data=json.dumps(body))
        logger.info(f'user join group Sent user_id and received {str(response.status_code)}')
        logger.info(f'user join group Sent user_id and received {str(response.content)}')
        if response.status_code != 200:
            await bot.send_message(event.chat.id, 'Произошла ошибка. Пожалуйста, обратитесь к команде проекта СВТ-31.')
        else:
            is_admin = await check_admin(bot, event.chat.id, user_id)
            body = {"group_id": event.chat.id, "user_id": user_id, "is_admin": is_admin}
            url = 'http://127.0.0.1:8000/add_group_member'
            response = requests.post(url, data=json.dumps(body))

            if response.status_code == 200:
                user_str = get_username_or_id(event.new_chat_member.user)
                await bot.send_message(event.chat.id, f'Добавлен пользователь {user_str}')
            else:
                await bot.send_message(event.chat.id, 'Произошла ошибка добавления пользователя.')


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def chat_member(event: ChatMemberUpdated, bot: Bot):
    """Пользователь выходит из группы / пользователя удаляют из группы"""
    user_id = event.new_chat_member.user.id
    if user_id != bot.id:
        body = {"group_id": event.chat.id, "user_id": user_id}
        url = 'http://127.0.0.1:8000/delete_group_member'
        response = requests.delete(url, data=json.dumps(body))
        if response.status_code == 200:
            user_str = get_username_or_id(event.new_chat_member.user)
            await bot.send_message(event.chat.id, f'Пользователь {user_str} лишен прав группы.')
        else:
            await bot.send_message(event.chat.id, 'Ошибка, пользователь не лишен прав группы.')
    else:
        # УДАЛИЛИ БОТА ИЗ ГРУППЫ
        pass


@router.message(Command('help', ignore_mention=True))
async def start(message: Message):
    """
    Функция, которая вызывается при команде help
    и выводит функционал бота
    """

    logger.info('Received the help command on group')

    await message.reply("""Функционал бота. 

Управление стендами с OBS:
/add_obs - Добавить стенд с OBS
/edit_obs - Редактировать стенд с OBS 
/delete_obs - Удалить стенд с OBS 
/check_obs - Показать все добавленные OBS
    
/start - повторный запрос на добавление группы""")




