import subprocess
import os
import signal
import time
import paho.mqtt.client as mqtt
from obswebsocket import obsws, requests
import json
from dotenv import load_dotenv

# variable fill by launch.py
WORK_DIRECTORY = "C:\IT\Autostreaming\AutostreamingOBS\\"

load_dotenv(WORK_DIRECTORY + ".env")
# get local variables
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
OBSWS_PASSWORD = os.getenv("OBSWS_PASSWORD")

if os.path.isfile(WORK_DIRECTORY + "config.json"):
    with open(WORK_DIRECTORY + "config.json") as f:
        config = json.load(f)
        OBSWS_HOST = config["obsws_host"]
        OBSWS_PORT = config["obsws_port"]
        OBS_PATH = config["obs_path"]
        MQTT_BROKER_HOST = config["mqtt_broker_host"]
        MQTT_BROKER_PORT = config["mqtt_broker_port"]
        MQTT_BROKER_KEEP_ALIVE_TIME = config["mqtt_broker_keep_alive_time"]
        UPDATE_LOOP_TIME = config["update_loop_time"]
else:
    exit("Error: config.json not found")

obs_ws = obsws(OBSWS_HOST, OBSWS_PORT, OBSWS_PASSWORD)
# check if obs is running before program was started
check_obs = subprocess.check_output('tasklist /fi "IMAGENAME eq obs64.exe" /fo "CSV"').decode(encoding="windows-1251")\
    .replace('"', '').split(",")
# !!! DANGER
if len(check_obs) == 9:
    # print("obs PID: ", check_obs[5])
    os.kill(int(check_obs[5]), signal.SIGTERM)
    time.sleep(2)
# else:
    # print("No obs detected!")

# start obs64.exe
# !!! obs_process.pid = pid of shell
if os.path.isfile(OBS_PATH + "\\" + "obs64.exe"):
    obs_process = subprocess.Popen(OBS_PATH + "\\" + "obs64.exe", cwd=OBS_PATH)
else:
    exit("OBS_PATH Error: obs64.exe not found")


def ping_sources() -> dict:
    obs_ws.connect()
    resp = dict()
    scenes = obs_ws.call(requests.GetSceneList())
    scenes_names = [scene["sceneName"] for scene in scenes.datain["scenes"]]
    for scene_name in scenes_names:
        sources = obs_ws.call(requests.GetSceneItemList(sceneName=scene_name))
        sources_names = [source["sourceName"] for source in sources.datain["sceneItems"]]
        resp[scene_name] = list()
        for source_name in sources_names:
            screenshot = obs_ws.call(requests.GetSourceScreenshot(sourceName=source_name, imageWidth=8, imageHeight=8,
                                             imageFormat="png")).datain["imageData"]
            state = False if len(screenshot) == 146 else True
            resp[scene_name].append({
                "source": source_name,
                "state": state
            })
    obs_ws.disconnect()
    return resp


# mqtt connection
def on_connect(client, userdata, flags, rc):
    # print("Connected with result code "+str(rc))
    client.subscribe("autostream/ping_sources")


def publish_ping(client, topic):
    msg = json.dumps({obs_name: ping_sources()})
    client.publish(topic, msg)
    # result = client.publish(topic, msg)
    # status = result[0]
    # if not status:
    #     print(f"Send {msg} to {topic}")
    # else:
    #     print(f"Failed to send message to topic {topic}")


def publish_state(client, topic, obs_state):
    msg = json.dumps(obs_state)
    client.publish(topic, msg)
    # result = client.publish(topic, msg)
    # status = result[0]
    # if not status:
    #     print(f"Send {msg} to {topic}")
    # else:
    #     print(f"Failed to send message to topic {topic}")


def on_message(client, userdata, msg):
    print(msg.payload)
    if b'PING_OBS' == msg.payload:
        publish_ping(client, msg.topic)
    # if json.loads(msg.payload) == "PING_OBS":
    #     publish_ping(client, msg.topic)


obs_name = OBSWS_HOST + ":" + str(OBSWS_PORT)
STATE_TOPIC = "autostream/obs_state"
PING_TOPIC = "autostream/ping_sources"
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
# connect_async to allow background processing
client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_TIME)
client.loop_start()

while True:
    time.sleep(UPDATE_LOOP_TIME)
    poll = obs_process.poll()
    time_stamp = time.time()
    error_msg = None
    if poll is None:
        state = True
        obs_state_msg = {
            "name": obs_name,
            "time": time_stamp,
            "state": state,
            "error_msg": error_msg
        }
        publish_state(client, STATE_TOPIC, obs_state_msg)
    else:
        state = False
        # try start obs64.exe
        if os.path.isfile(OBS_PATH + "\\" + "obs64.exe"):
            obs_process = subprocess.Popen(OBS_PATH + "\\" + "obs64.exe", cwd=OBS_PATH)
        else:
            error_msg = "OBS_PATH Error: obs64.exe not found"

        obs_state_msg = {
            "name": obs_name,
            "time": time_stamp,
            "state": state,
            "error_msg": error_msg
        }
        publish_state(client, STATE_TOPIC, obs_state_msg)
