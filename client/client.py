import subprocess
import os
import signal
import time
import logging
import socket
import asyncio
import json
import paho.mqtt.client as mqtt
import simpleobsws
from dotenv import load_dotenv


global OBSWS_HOST, OBSWS_PORT, OBS_PATH, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_TIME, \
    UPDATE_LOOP_TIME, OBS_NAME, STATE_TOPIC, PING_TOPIC
global MQTT_USERNAME, MQTT_PASSWORD, OBSWS_PASSWORD


WORK_DIRECTORY = os.getcwd() + "\\"

log = logging.getLogger("client")
log.setLevel(logging.INFO)
log_handler = logging.FileHandler("client.log")
log_handler.setFormatter(logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s"))
log.addHandler(log_handler)


def async_loop(func):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(func(*args, **kwargs))
        return resp
    return wrapper


def get_curr_ip() -> str:
    return socket.gethostbyname(socket.gethostname())


def check_configure(path: str) -> bool:
    return os.path.isfile(path + "config.json")


def get_obs_pid() -> int or None:
    def obs_is_running(check_obs: list) -> bool:
        # 9 - length of shell output if obs process was found
        return len(check_obs) == 9

    obs_pid = None
    shell_output = subprocess.check_output('tasklist /fi "IMAGENAME eq obs64.exe" /fo "CSV"').decode(
        encoding="windows-1251").replace('"', '').split(",")

    if obs_is_running(shell_output):
        obs_pid = int(shell_output[5])

    return obs_pid


def kill_process(pid: int):
    # !!! DANGER
    os.kill(pid, signal.SIGTERM)


def check_obs_path(path: str) -> bool:
    return os.path.isfile(path + "\\" + "obs64.exe")


def start_obs_process() -> subprocess.Popen or None:
    # !!! obs_process.pid = pid of shell
    obs_process = None

    if check_obs_path(OBS_PATH):
        obs_process = subprocess.Popen(OBS_PATH + "\\" + "obs64.exe", cwd=OBS_PATH)

    return obs_process


@async_loop
async def ping_sources() -> dict:
    obsws = create_obsws_client(OBSWS_HOST, OBSWS_PORT, OBSWS_PASSWORD)

    resp = dict()
    await obsws.connect()
    await obsws.wait_until_identified()

    ret = await obsws.call(simpleobsws.Request("GetSceneList"))

    if not ret.ok():
        log.error("obs websockets: failed GetSceneList")
        await obsws.disconnect()
        return resp

    scenes = ret.responseData
    scenes_names = [scene["sceneName"] for scene in scenes["scenes"]]

    for scene_name in scenes_names:
        resp[scene_name] = list()
        ret = await obsws.call(simpleobsws.Request("GetSceneItemList", requestData={'sceneName': scene_name}))

        if not ret.ok():
            log.error("obs websockets: failed GetSceneItemList for Scene: " + scene_name)
            continue

        sources = ret.responseData
        gstreamer_sources_names = [source["sourceName"] for source in sources["sceneItems"]
                                   if source["inputKind"] == "gstreamer-source"]

        for source_name in gstreamer_sources_names:
            screen_req = simpleobsws.Request("GetSourceScreenshot", requestData={
                "sourceName": source_name, "imageWidth": 8, "imageHeight": 8, "imageFormat": "png"
            })
            ret = await obsws.call(screen_req)

            if not ret.ok():
                log.error("obs websockets: failed GetSourceScreenshot for Source: " + source_name)
                continue

            screenshot = ret.responseData["imageData"]
            # 146 - length of base64 data string about empty png image
            state = False if len(screenshot) == 146 else True

            resp[scene_name].append({
                "source": source_name,
                "state": state
            })

    await obsws.disconnect()
    return resp


@async_loop
async def check_obsws_connection(host: str = "", port: int = 0, password: str = "",
                                 obsws: simpleobsws.WebSocketClient = None) -> bool:
    if obsws:
        ws = obsws
    else:
        ws = create_obsws_client(host, port, password)
    try:
        await ws.connect()
    except ConnectionRefusedError:
        return False
    await ws.wait_until_identified()
    ret = await ws.call(simpleobsws.Request("GetVersion"))
    await ws.disconnect()

    if ret.ok():
        return True
    else:
        return False


@async_loop
async def run_obsws_request(req: str, data: dict) -> dict:
    obsws = create_obsws_client(OBSWS_HOST, OBSWS_PORT, OBSWS_PASSWORD)
    await obsws.connect()
    await obsws.wait_until_identified()

    ret = await obsws.call(simpleobsws.Request(req, data))
    await obsws.disconnect()

    if not ret.ok():
        log.error(f"obs websockets: failed on remote command:{req}\nwith data:{data}")
        return {"error": True}

    return ret.responseData


def create_obsws_client(host: str, port: int, password: str) -> simpleobsws.WebSocketClient:
    parameters = simpleobsws.IdentificationParameters(ignoreNonFatalRequestChecks=False)
    obs_ws_client = simpleobsws.WebSocketClient(url=f'ws://{host}:{port}', password=password,
                                                identification_parameters=parameters)
    return obs_ws_client


def change_obsws_creds(host: str, port: int, password: str, name: str = ""):
    global OBSWS_HOST
    global OBSWS_PORT
    global OBSWS_PASSWORD
    global OBS_NAME

    OBSWS_HOST = host
    OBSWS_PORT = port
    OBSWS_PASSWORD = password
    if name:
        OBS_NAME = name
    else:
        OBS_NAME = OBSWS_HOST + ":" + str(OBSWS_PORT)


def save_configure():
    config = dict()
    config["obsws"]["host"] = OBSWS_HOST
    config["obsws"]["port"] = OBSWS_PORT
    config["obs_path"] = OBS_PATH
    config["mqtt"]["host"] = MQTT_BROKER_HOST
    config["mqtt"]["port"] = MQTT_BROKER_PORT
    config["mqtt"]["keep_alive_time"] = MQTT_BROKER_KEEP_ALIVE_TIME
    config["update_loop_time"] = UPDATE_LOOP_TIME
    config["obs_name"] = OBS_NAME
    config["mqtt"]["state_topic"] = STATE_TOPIC
    config["mqtt"]["ping_topic"] = PING_TOPIC

    with open("config.json", "w") as f:
        json.dump(config, f)


def save_env():
    with open(".env", "w") as f:
        f.write("MQTT_USERNAME=" + MQTT_USERNAME + "\n")
        f.write("MQTT_PASSWORD=" + MQTT_PASSWORD + "\n")
        f.write("OBSWS_PASSWORD=" + OBSWS_PASSWORD + "\n")


def check_router_reboot():
    if not check_obsws_connection(OBSWS_HOST, OBSWS_PORT, OBSWS_PASSWORD):
        curr_ip = get_curr_ip()

        if curr_ip != OBSWS_HOST and check_obsws_connection(curr_ip, OBSWS_PORT, OBSWS_PASSWORD):
            log.warning(f"obs if was changed from {OBSWS_HOST} to {curr_ip}")
            # resp = {
            #     "name": OBS_NAME,
            #     "old_ip": OBSWS_HOST,
            #     "port": OBSWS_PORT,
            #     "new_ip": curr_ip
            # }
            change_obsws_creds(curr_ip, OBSWS_PORT, OBSWS_PASSWORD)
            save_configure()
            # дёргать ручку МУ
        else:
            log.critical(f"obs credentials were changed. Failed connection to obs websockets with host:"
                         f" {OBSWS_HOST}:{OBSWS_PORT}")
            complete_program()


def create_mqtt_client(username: str, password: str, host: str, port: int) -> mqtt.Client or None:
    def check_mqtt_connection(client: mqtt.Client, host: str, port: int) -> bool:
        client.connect_async(host, port)
        client.loop_start()
        # sleep!
        time.sleep(0.5)
        state = client.is_connected()
        client.loop_stop()

        if state:
            client.disconnect()

        return state

    client = mqtt.Client()
    client.username_pw_set(username, password)

    if check_mqtt_connection(client, host, port):
        client.on_connect = on_connect
        client.on_message = on_message
        return client

    return None


def complete_program():
    obs_process.kill()
    log.info("obs was killed")
    log.critical("program completed")


def poll_process(process: subprocess.Popen) -> dict:
    poll = process.poll()
    time_stamp = time.strftime("%Y.%m.%d %H:%M:%S")
    state = poll is None
    msg = {
        "name": OBS_NAME,
        "time": time_stamp,
        "state": state,
    }
    return msg


def read_configure():
    global OBSWS_HOST, OBSWS_PORT, OBS_PATH, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_TIME, \
        UPDATE_LOOP_TIME, OBS_NAME, STATE_TOPIC, PING_TOPIC

    if os.path.isfile(WORK_DIRECTORY + "config.json"):
        with open(WORK_DIRECTORY + "config.json") as f:
            config = json.load(f)
            OBSWS_HOST = config["obsws"]["host"]
            OBSWS_PORT = config["obsws"]["port"]
            OBS_PATH = config["obs_path"]
            MQTT_BROKER_HOST = config["mqtt"]["host"]
            MQTT_BROKER_PORT = config["mqtt"]["port"]
            MQTT_BROKER_KEEP_ALIVE_TIME = config["mqtt"]["keep_alive_time"]
            UPDATE_LOOP_TIME = config["update_loop_time"]
            OBS_NAME = config["obs_name"]
            STATE_TOPIC = config["mqtt"]["state_topic"]
            PING_TOPIC = config["mqtt"]["ping_topic"]
    else:
        log.error("config file does not exist!")


def read_env():
    global MQTT_USERNAME, MQTT_PASSWORD, OBSWS_PASSWORD

    MQTT_USERNAME = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
    OBSWS_PASSWORD = os.getenv("OBSWS_PASSWORD")


# MQTT connection
def on_connect(client, userdata, flags, rc):
    if not rc:
        log.info(f"mqtt connected to broker with result code {rc}")
    else:
        log.error(f"mqtt connected to broker with result code {rc}")

    client.subscribe("autostream/#")


def publish_ping(client, topic):
    check_router_reboot()

    ping = ping_sources()
    msg = json.dumps({OBS_NAME: ping})
    '''
    {OBS_NAME: {
                scene_name: [ {"source": source_name, "state": True}, {"source": source_name2, "state": False}, {}],
                scene_name2: [ {}, {}, {}],
                ...
                }
    }
    '''
    result = client.publish(topic, msg, qos=2)
    status = result[0]

    if status:
        log.warning(f"Failed to send message to topic {topic}")
    else:
        log.info("ping published")


def publish_state(client, topic, obs_state):
    msg = json.dumps(obs_state)
    result = client.publish(topic, msg)
    status = result[0]

    if status:
        log.warning(f"Failed to send message to topic {topic}")


def publish_ws(client, topic, data):
    msg = json.dumps(data)
    result = client.publish(topic, msg, qos=2)
    status = result[0]

    if status:
        log.warning(f"Failed to send message to topic {topic}")
    else:
        log.info("obs websocket response for request published")


def on_message(client, userdata, msg):
    # PING_OBS - special command that sign client app to do and send ping data
    # if msg.payload == OBS_NAME:
    req = json.loads(msg.payload)
    if req == "PING_OBS":
        publish_ping(client, msg.topic)
    elif msg.topic == "autostream/" + OBS_NAME + "/requests":
        log.info(f"OBWSW REQUEST\nid:{req['obs_name']}\nrequest:{req['request']}")
        resp = run_obsws_request(req["request"], req["data"])
        publish_ws(client, "autostream/" + OBS_NAME + "/responses", resp)


# get local variables
load_dotenv(WORK_DIRECTORY + ".env")
read_env()

if not(MQTT_USERNAME and MQTT_PASSWORD and OBSWS_PASSWORD):
    log.critical(f"environment variables are empty. Path to env-file: {WORK_DIRECTORY + '.env'}")
    exit("Error: .env file not found")

if check_configure(WORK_DIRECTORY):
    read_configure()
else:
    log.critical(f"config.json not found. Path to config-file: {WORK_DIRECTORY + 'config.json'}")
    exit("Error: config.json not found")

# check if obs is running before program was started
obs_pid = get_obs_pid()

if obs_pid is not None:
    kill_process(obs_pid)
    log.info("obs was killed")
    # sleep!
    time.sleep(5)

# start obs64.exe
obs_process = start_obs_process()


if not obs_process:
    log.critical("obs process was not created. Path to obs-file: " + OBS_PATH + "\\" + "obs64.exe")
    exit("Error: obs64.exe file not found")
else:
    log.info("obs was started")

# create obs websockets client
count = 0

while not check_obsws_connection(OBSWS_HOST, OBSWS_PORT, OBSWS_PASSWORD) and count < 5:
    log.error(f"obs websocket connection failed with host: {OBSWS_HOST}:{OBSWS_PORT}")
    # sleep!
    time.sleep(2)

# create mqtt_client
mqtt_client = create_mqtt_client(MQTT_USERNAME, MQTT_PASSWORD, MQTT_BROKER_HOST, MQTT_BROKER_PORT)

if mqtt_client is None:
    log.critical(f"Mqtt connection failed.\nMqtt broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    exit("Error: failed")

if mqtt_client:
    # connect_async to allow background processing
    mqtt_client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_TIME)
    mqtt_client.loop_start()

    while True:
        # sleep!
        time.sleep(UPDATE_LOOP_TIME)
        obs_state_msg = poll_process(obs_process)
        publish_state(mqtt_client, STATE_TOPIC, obs_state_msg)

        if not obs_state_msg["state"]:
            # try restart obs64.exe 3 times
            try_count = 1
            log.info("obs restarting")
            obs_process = start_obs_process()

            while obs_process is None and try_count <= 3:
                # sleep !
                time.sleep(1)
                log.error(f"obs failed to restart. try: {try_count}")
                obs_process = start_obs_process()
                try_count += 1

complete_program()
