# Создайте файл .env
Пример файла:
```
BOT_TOKEN=6030500018:AAFM4cНQnSGXNO-XSO1GpJEP9hmq_FMzfvU
KEY=yi86wOdz38K1psqCRAxBDoltR-rc2gBcq35_lZihAnc=
```

В него нужно вписать две вещи: токен телеграм-бота и ключ шифрования информации в БД
1. Токен можно взять в Телеграм-боте BotFather (https://t.me/BotFather): введите команду /mybots, выберите своего бота и нажмите на кнопку ```API Token```
2. Ключ шифрования вы можете сгенерировать, запустив следующий код на Python:
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key)
```

# Запустите проект через докер
```
docker-compose build
docker-compose up -d
```

или то же самое в одну строку

```
docker-compose build && docker-compose up -d
```

**Если ошибка:**
```
ERROR: for obs  "host" network_mode is incompatible with port_bindings
```
**То обновите свой докер**

## Накатить миграции на бд
```
alembic upgrade head
```
Если возникает ошибка: ```-bash: alembic: command not found```,
cоздайте виртуальное окружение по этому гайду:
https://timeweb.cloud/tutorials/python/kak-sozdat-virtualnoe-okruzhenie
и скачайте туда дополнения следующим образом:
```
pip install alembic psycopg2-binary sqlalchemy
```
После этого можете накатить миграции
```
alembic upgrade head
```

## Запуск на локальном устройстве без докеров
1. Запустите бота при помощи
```
python bot.py
```
или напрямую из IDE
2. Поднимите базу данных Redis
```
docker run -p  127.0.0.1:6379:6379 redis:latest
```
3. Запустите обс-сервис при помощи
```
uvicorn main:app --host 0.0.0.0 --port 8000
```
