import paho.mqtt.client as mqtt
import json
import time
from os import getenv
from dotenv import load_dotenv

# подключение к брокеру (вызывается автоматически)
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("autostream/#")

# для отправки сообщения в topic
def publish(client, topic):
    # обязательно переводить в json-строку!
    # сообщение PING_OBS вызывает функцию пингования источников на клиентской обс
    msg = json.dumps("PING_OBS")
    result = client.publish(topic, msg)
    status = result[0]
    if not status:
        print(f"Send {msg} to {topic}")
    else:
        print(f"Failed to send message to topic {topic}")

# callback на появление сообщения в topic
def on_message(client, userdata, msg):
    if json.loads(msg.payload) != "PING_OBS":
        print(json.loads(msg.payload))


topic = "autostream/ping_sources"
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# имя и пароль хранятся в локальных переменных!
load_dotenv()
USERNAME = getenv("NAME")
PASSWORD = getenv("PASSWORD")

client.username_pw_set(USERNAME, PASSWORD)

# connect_async to allow background processing
client.connect_async("172.18.130.40", 1883, 60)
client.loop_start()

# тут нужно написать цикл для отправки сообщений в topic
while True:
    time.sleep(8)
    publish(client, topic)
