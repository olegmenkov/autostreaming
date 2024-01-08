
# Запуск через докер
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
