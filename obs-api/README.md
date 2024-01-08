# OBS-server
Сервер работает на порте 8000
## Docker
Для запуска приложения в докер-контейнере напишите
```
docker build -t cbt .
docker run -p 8000:8000 cbt 
```
## Redis
Для того чтобы база данных работала напишите
```
docker run -p  127.0.0.1:6379:6379 redis:latest
```
