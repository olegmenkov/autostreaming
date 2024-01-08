import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import bot_command_scope_all_private_chats, bot_command_scope_all_chat_administrators
from dotenv import load_dotenv
import commands
import private_handlers, group_handlers

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN)


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


if __name__ == '__main__':
    asyncio.run(main())
