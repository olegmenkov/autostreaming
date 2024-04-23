import paho.mqtt.client as mqtt
import json
import time
from os import getenv
from dotenv import load_dotenv


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("autostream/#")


# def publish(client, topic):
#     msg = json.dumps("PING_OBS")
#     result = client.publish(topic, msg)
#     status = result[0]
#     if not status:
#         print(f"Send {msg} to {topic}")
#     else:
#         print(f"Failed to send message to topic {topic}")


def on_message(client, userdata, msg):
    state = json.loads(msg.payload)
    print(state)


topic = "autostream/obs_state"
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
# get local variables
load_dotenv()
USERNAME = getenv("NAME")
PASSWORD = getenv("PASSWORD")

client.username_pw_set(USERNAME, PASSWORD)
# connect_async to allow background processing
client.connect_async("172.18.130.40", 1883, 60)
client.loop_forever()
# client.loop_start()

# utility modul loop will change this for sending request to client when it necessary
# while True:
#     time.sleep(8)
#     publish(client, topic)
