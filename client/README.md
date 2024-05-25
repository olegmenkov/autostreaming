# AutostreamingOBS

Проект является частью более крупного проекта по удалённому управлению режесёрского пульта с использованием свободного програмного обеспечения OBS studio

## Предустановки
1. OBS Studio v29.1.3 и выше
2. Python v3.11 и выше

## Регламент установки клиентского приложения Autostreaming

1. Склонировать репозиторий AutostreamingClient
```
git clone https://github.com/gPlorovg/AutostreamingClient.git
```
2. Открыть powershell и перейти в папку с проектом
3. Установить все зависимости (для глобального Python интерпретатора)
```
pip install -r requirements.txt
```
4. Запустить файл "launch.py" и ввести необходимые данные 
(убедитесь, что ОБС запускается и работают вебсокеты, а также есть доступ к MQTT брокеру, т.е. включён впн)
```
python .\launch.py
```
6. Сохранить команду для автозапуска клиентского приложения
```
Autorun command for Autostreaming client app:
<DATA>
```
7. Запустить от имени Администратора powershell
8. Ввести полученнию команду (DATA). Полученный вывод:
```
УСПЕХ. Запланированная задача "Autostreaming" была успешно создана.
```
9. Запустить клиентское приложение
```
pythonw.exe .\client.py
```

### Клиентское приложение

Скрипт client.py запускается в фоновом режиме с помощью pythonw.exe
Клиентское приложение предоставляет 3 главных функции:
1. Поддержание ОБС во включённом состоянии
2. Выполнение удалённых ОБС Вебсокет запросов и отправка ответа
3. Уведомление пользователей если один из источников(ртсп-камера) становится недоступным
4. 
Client provided 3 main ability:
1. Maintain obs in active state
2. Run remote obsws requests and send responses
3. Notify users if one of obs sources(rtsp-cameras) is unavailable
