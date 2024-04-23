from aiogram.types import BotCommand

  # Команды под кнопкой menu в личных сообщениях
private = {
    '/start': 'Начать работу с ботом',
    '/help': 'Посмотреть функционал бота',
    '/check_obs': 'Показать добавленные OBS',
    '/add_obs': 'Добавить стенд с OBS',
    '/edit_obs': 'Изменить данные о стенде с OBS',
    '/delete_obs': 'Удалить стенд с OBS',
    '/plan_stream': 'Запланировать стрим',
    '/plan_recording': 'Запланировать запись',
    '/plan_stream_recording': 'Запланировать стрим+запись',
    '/start_stream': 'Запустить стрим вручную прямо сейчас',
    '/stop_stream': 'Остановить стрим вручную прямо сейчас',
    '/start_recording': 'Запустить запись',
    '/stop_recording': 'Остановить запись',
    '/get_scenes': 'Посмотреть информацию о сценах',
    '/set_scene': 'Переключить сцену в Program',
    '/ping_obs': 'Проверить доступность стенда с OBS',
    '/ping_stream': 'Проверить, запущен ли стрим',
    '/ping_recording': 'Проверить, запущена ли запись'
           }

# Команды под кнопкой menu в групповых сообщениях
group = {
    '/start': 'Запрос на добавление группы',
    '/help': 'Посмотреть функционал бота',
    '/check_obs': 'Показать добавленные OBS',
    '/add_obs': 'Добавить стенд с OBS',
    '/edit_obs': 'Изменить данные о стенде с OBS',
    '/delete_obs': 'Удалить стенд с OBS',
    # '/plan_stream': 'Запланировать стрим',
    # '/start_stream': 'Запустить стрим вручную прямо сейчас',
    # '/stop_stream': 'Остановить стрим вручную прямо сейчас',
    # '/start_recording': 'Запустить запись',
    # '/stop_recording': 'Остановить запись',
    # '/get_scenes': 'Посмотреть информацию о сценах',
    # '/set_scene': 'Переключить сцену в Program',
    # '/ping_obs': 'Проверить доступность стенда с OBS',
    # '/ping_stream': 'Проверить, запущен ли стрим',
    # '/ping_recording': 'Проверить, запущена ли запись'
        }

private_commands = []
group_commands = []

for k, v in private.items():
    private_commands.append(BotCommand(command=k, description=v))

for k, v in group.items():
    group_commands.append(BotCommand(command=k, description=v))
