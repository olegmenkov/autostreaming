import subprocess
import os
import signal
import time
import paho.mqtt.client as mqtt
# from obswebsocket import obsws, requests
import json
from dotenv import load_dotenv

# variable fill by launch.py
WORK_DIRECTORY = "C:\IT\Autostreaming\AutostreamingOBS\\"

load_dotenv(WORK_DIRECTORY + ".env")
# obs websocket connection
# obs_host = "localhost"
# obs_port = 4455
# obs_password = "TKoxvvk9TPgJNkt4"
# obs = obsws(obs_host, obs_port, obs_password)

if os.path.isfile(WORK_DIRECTORY + "config.conf"):
    with open(WORK_DIRECTORY + "config.conf") as f:
        OBS_PATH = f.readline()

# check if obs is running before program was started
check_obs = subprocess.check_output('tasklist /fi "IMAGENAME eq obs64.exe" /fo "CSV"').decode(encoding="windows-1251")\
    .replace('"', '').split(",")

# !!! DANGER
if len(check_obs) == 9:
    print("obs PID: ", check_obs[5])
    os.kill(int(check_obs[5]), signal.SIGTERM)
else:
    print("No obs detected!")

# start obs64.exe
# !!! obs_process.pid - pid of shell
if os.path.isfile(OBS_PATH + "\\" + "obs64.exe"):
    obs_process = subprocess.Popen(OBS_PATH + "\\" + "obs64.exe", cwd=OBS_PATH)
# else:
#     OBS_PATH = find()
#     with open("config.conf", "w") as f:
#         f.write(OBS_PATH)
#     obs_process = subprocess.Popen(OBS_PATH + "\\" + "obs64.exe", cwd=OBS_PATH)

# mqtt connection
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("autostream")


def publish(client, topic, obs_status):
    msg = json.dumps(obs_status)
    result = client.publish(topic, msg)
    status = result[0]
    if not status:
        print(f"Send {msg} to {topic}")
    else:
        print(f"Failed to send message to topic {topic}")


# def on_message(client, userdata, msg):
#     if json.loads(msg.payload) == "PING_OBS":
#         publish(client, msg.topic)

loop_time = 1
client_name = "machine_1"
topic = "autostream/obs_state"
client = mqtt.Client()
client.on_connect = on_connect
# client.on_message = on_message
# get local variables

USERNAME = os.getenv("NAME")
PASSWORD = os.getenv("PASSWORD")

client.username_pw_set(USERNAME, PASSWORD)
# connect_async to allow background processing
client.connect_async("172.18.130.40", 1883, 60)

client.loop_start()
while True:
    time.sleep(loop_time)
    poll = obs_process.poll()
    if poll is None:
        publish(client, topic, "UP " + client_name)
    else:
        publish(client, topic, "DOWN " + client_name)
        # start obs64.exe
        if os.path.isfile(OBS_PATH + "\\" + "obs64.exe"):
            obs_process = subprocess.Popen(OBS_PATH + "\\" + "obs64.exe", cwd=OBS_PATH)
