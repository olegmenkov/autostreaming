# О проекте
Автостриминг - это сервис, который позволяет удаленно управлять съемочными студиями и контролировать трансляции и записи. С помощью нашего телеграм бота или удобного интерфейса календаря пользователь может легко создать событие для трансляции или записи, указав время начала и окончания. И самое замечательное - все происходит автоматически! Как это работает? Все просто: пользователь выбирает нужную команду в телеграмм боте, который отправляет запрос на наш сервер - в модуль управления. Затем модуль управления связывается с OBS и выполняет все необходимые действия. Таким образом, пользователь получает полный контроль над процессом трансляции или записи без необходимости находиться на месте. 

# Как запустить сервис
## 1. Склонируйте репозиторий
```
git clone https://github.com/olegmenkov/autostreaming.git
```

## 2. Создайте файл ```.env``` в корневой директории (в папке autostreaming)
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

## 2. Запустите проект через докер
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

# А как...

## ... накатить миграции на бд
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

## ... запустить проект без докеров
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
