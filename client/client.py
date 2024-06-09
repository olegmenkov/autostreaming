"""
Client provided 3 main ability:
1. Maintain obs in active state
2. Run remote obsws requests and send responses
3. Notify users if one of obs sources(rtsp-cameras) is unavailable
"""
import os
import signal
import time
import subprocess
import logging
import asyncio
import json
import paho.mqtt.client as mqtt
import simpleobsws
from dotenv import load_dotenv


global OBSWS_HOST, OBSWS_PORT, OBS_PATH, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_TIME, \
    UPDATE_LOOP_TIME, OBS_NAME, STATE_TOPIC, PING_TOPIC, REQUEST_TOPIC, RESPONSE_TOPIC
global MQTT_USERNAME, MQTT_PASSWORD, OBSWS_PASSWORD


WORK_DIRECTORY = os.getcwd() + "\\"

log = logging.getLogger("client")
log.setLevel(logging.INFO)
log_handler = logging.FileHandler("client.log")
log_handler.setFormatter(logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s"))
log.addHandler(log_handler)


def async_loop(func):
    """Decorator for async functions to run in synchronously"""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        resp = loop.run_until_complete(func(*args, **kwargs))
        return resp
    return wrapper


# def get_curr_ip() -> str:
#     return socket.gethostbyname(socket.gethostname())


def check_configure(path: str) -> bool:
    """Check if config file exists"""
    return os.path.isfile(path + "config.json")


def get_obs_pid() -> int or None:
    """If obs is running return pid of obs64.exe process, if not then return None"""
    def obs_is_running(check_obs: list) -> bool:
        """9 - length of shell output if obs process was found"""
        # 9 - length of shell output if obs process was found
        return len(check_obs) == 9

    obs_pid = None
    shell_output = subprocess.check_output('tasklist /fi "IMAGENAME eq obs64.exe" /fo "CSV"').decode(
        encoding="windows-1251").replace('"', '').split(",")

    if obs_is_running(shell_output):
        obs_pid = int(shell_output[5])

    return obs_pid


def kill_process(pid: int):
    """
    Warning!!!
    Kill obs64.exe process to be able to run it again as subprocess object
    """
    os.kill(pid, signal.SIGTERM)


def check_obs_path(path: str) -> bool:
    """Check if obs64.exe exists in path"""
    return os.path.isfile(path + "\\" + "obs64.exe")


def start_obs_process(obs_path: str) -> subprocess.Popen or None:
    """
    Start obs64.exe process
    :return process if success
    :return None if faild
    !!! obs_process.pid is pid of shell, no pid of obs64.exe
    """
    obs_process = None

    if check_obs_path(obs_path):
        obs_process = subprocess.Popen(obs_path + "\\" + "obs64.exe --disable-shutdown-check", cwd=obs_path)

    return obs_process


@async_loop
async def ping_sources() -> dict:
    """
    Connect to obsws, GetSceneList, for each scene GetSceneItemList,
    extract sources with parameter inputKind = 'gstreamer-source',
    for extracted sources GetSourceScreenshot 8x8 .png,
    if imageData - base64 data string length = 146, then 8x8 .png image is empty, so it's mean that source is inactive
    :return:{
                scene_name: [{"source": str, "state": bool}, ...],
                ...
            }
    """
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
            state = False if len(screenshot) == 146 else True

            resp[scene_name].append({
                "source": source_name,
                "state": state
            })

    await obsws.disconnect()
    return resp


async def check_obsws_connection(host: str = "", port: int = 0, password: str = "",
                                 obsws: simpleobsws.WebSocketClient = None) -> bool:
    """
    Check if credentials for obsws connection are correct if obsws parameter wasn't passed
    Check if obsws object is able to connect if obsws parameter was passed
    """
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

# check_obsws_connection_loop - synchronous function
check_obsws_connection_loop = async_loop(check_obsws_connection)


@async_loop
async def run_obsws_request(req: str, data: dict, password: str) -> dict:
    """
    Run request on obs by websockets and give response
    :param req: obsws request (like 'GetVersion')
    :param data: obsws reques additional data (like {"scene": scene_name})
    :param password: obsws password
    :return:{
                "data": responseData / None,
                "error": None / "wrong password" / f"failed on remote command:{req}\nwith data:{data}"
            }
    """
    obsws = create_obsws_client(OBSWS_HOST, OBSWS_PORT, password)

    if not await check_obsws_connection(obsws=obsws):
        log.error(f"obs websockets: failed on remote command:{req}\nwith data:{data}\nWRONG PASSWORD!")
        return {"data": None, "error": "wrong password"}

    await obsws.connect()
    await obsws.wait_until_identified()

    ret = await obsws.call(simpleobsws.Request(req, data))
    await obsws.disconnect()

    if not ret.ok():
        log.error(f"obs websockets: failed on remote command:{req}\nwith data:{data}")
        return {"data": None, "error": f"failed on remote command:{req}\nwith data:{data}"}

    return {"data": ret.responseData, "error": None}


def create_obsws_client(host: str, port: int, password: str) -> simpleobsws.WebSocketClient:
    """:return: created from creds obsws object"""
    parameters = simpleobsws.IdentificationParameters(ignoreNonFatalRequestChecks=False)
    obs_ws_client = simpleobsws.WebSocketClient(url=f'ws://{host}:{port}', password=password,
                                                identification_parameters=parameters)
    return obs_ws_client


# def change_obsws_creds(host: str, port: int, password: str, name: str = ""):
#     global OBSWS_HOST
#     global OBSWS_PORT
#     global OBSWS_PASSWORD
#     global OBS_NAME
#
#     OBSWS_HOST = host
#     OBSWS_PORT = port
#     OBSWS_PASSWORD = password
#     if name:
#         OBS_NAME = name
#     else:
#         OBS_NAME = OBSWS_HOST + ":" + str(OBSWS_PORT)


# def save_configure():
#     config = dict()
#     config["obsws"]["host"] = OBSWS_HOST
#     config["obsws"]["port"] = OBSWS_PORT
#     config["obs_path"] = OBS_PATH
#     config["mqtt"]["host"] = MQTT_BROKER_HOST
#     config["mqtt"]["port"] = MQTT_BROKER_PORT
#     config["mqtt"]["keep_alive_time"] = MQTT_BROKER_KEEP_ALIVE_TIME
#     config["update_loop_time"] = UPDATE_LOOP_TIME
#     config["obs_name"] = OBS_NAME
#     config["mqtt"]["state_topic"] = STATE_TOPIC
#     config["mqtt"]["ping_topic"] = PING_TOPIC
#
#     with open("config.json", "w") as f:
#         json.dump(config, f)


# def save_env():
#     with open(".env", "w") as f:
#         f.write("MQTT_USERNAME=" + MQTT_USERNAME + "\n")
#         f.write("MQTT_PASSWORD=" + MQTT_PASSWORD + "\n")
#         f.write("OBSWS_PASSWORD=" + OBSWS_PASSWORD + "\n")


# def check_router_reboot():
#     if not check_obsws_connection_loop(OBSWS_HOST, OBSWS_PORT, OBSWS_PASSWORD):
#         curr_ip = get_curr_ip()
#
#         if curr_ip != OBSWS_HOST and check_obsws_connection_loop(curr_ip, OBSWS_PORT, OBSWS_PASSWORD):
#             log.warning(f"obs if was changed from {OBSWS_HOST} to {curr_ip}")
#             # resp = {
#             #     "name": OBS_NAME,
#             #     "old_ip": OBSWS_HOST,
#             #     "port": OBSWS_PORT,
#             #     "new_ip": curr_ip
#             # }
#             change_obsws_creds(curr_ip, OBSWS_PORT, OBSWS_PASSWORD)
#             save_configure()
#             # дёргать ручку МУ
#         else:
#             log.critical(f"obs credentials were changed. Failed connection to obs websockets with host:"
#                          f" {OBSWS_HOST}:{OBSWS_PORT}")
#             complete_program()


def create_mqtt_client(username: str, password: str, host: str, port: int) -> mqtt.Client or None:
    """
    Create mqtt client object
    If success return client object
    If faild return None
    """
    def check_mqtt_connection(client: mqtt.Client, host: str, port: int) -> bool:
        """
        Check if credentials for mqtt connection are correct
        Has sleep 0.5s!
        """
        client.connect_async(host, port)
        client.loop_start()
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
    """
    Warning!!!
    kill obs64.exe process
    Emergency shutdown
    """
    obs_process.kill()
    log.info("obs was killed")
    log.critical("program completed")


def poll_process(process: subprocess.Popen) -> dict:
    """
    Check if obs64.exe is running
    :return:{
                "name": str (like 172.23.43.22:4455),
                "time": str (like %Y.%m.%d %H:%M:%S),
                "state": bool,
            }
    """
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
    """Gets information from config.json to global variables to use it"""
    global OBSWS_HOST, OBSWS_PORT, OBS_PATH, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_TIME, \
        UPDATE_LOOP_TIME, OBS_NAME, STATE_TOPIC, PING_TOPIC, REQUEST_TOPIC, RESPONSE_TOPIC

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
            REQUEST_TOPIC = config["mqtt"]["request_topic"]
            RESPONSE_TOPIC = config["mqtt"]["response_topic"]
    else:
        log.error("config file does not exist!")


def read_env():
    """Gets information from .env to global variables to use it"""
    global MQTT_USERNAME, MQTT_PASSWORD, OBSWS_PASSWORD

    MQTT_USERNAME = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
    OBSWS_PASSWORD = os.getenv("OBSWS_PASSWORD")


def on_connect(client, userdata, flags, rc):
    """
    Callback function for mqtt client, execute when try to connect to mqtt broker
    Subscribe client to all autostream topics
    """
    if not rc:
        log.info(f"mqtt connected to broker with result code {rc}")
    else:
        log.error(f"mqtt connected to broker with result code {rc}")

    client.subscribe("autostream/#")


# def publish_ping(client, topic):
#     check_router_reboot()
#
#     ping = ping_sources()
#     msg = json.dumps({OBS_NAME: ping})
#     '''
#     {OBS_NAME: {
#                 scene_name: [ {"source": source_name, "state": True}, {"source": source_name2, "state": False}, {}],
#                 scene_name2: [ {}, {}, {}],
#                 ...
#                 }
#     }
#     '''
#     result = client.publish(topic, msg)
#     status = result[0]
#
#     if status:
#         log.warning(f"Failed to send message to topic {topic}")
#     else:
#         log.info("ping published")
def publish_ping_fail(client: mqtt.Client, topic: str):
    """
    Ping obs sources by ping_sources() function and publish all failed sources to mqtt broker
    ping
    {
        scene_name: [ {"source": source_name, "state": True}, {"source": source_name2, "state": False}, {}],
        scene_name2: [ {}, {}, {}],
        ...
    }
    msg
    {
        "obs_name": str (like 172.23.5.20:4455)
        "fails": {scene_name:[failed_source_name, ...], ...}
    }
    :param client: mqtt client
    :param topic: topic for obs source ping (like autostream/ping_sources)
    """
    # check_router_reboot()

    ping = ping_sources()
    fails = dict()

    for scene in ping:
        scene_fails = list()
        for source in ping[scene]:
            if not source["state"]:
                scene_fails.append(source["source"])
        if scene_fails:
            fails[scene] = scene_fails

    if fails:
        msg = json.dumps({"obs_name": OBS_NAME, "fails": fails})
        result = client.publish(topic, msg)
        status = result[0]

        if status:
            log.warning(f"Failed to send message to topic {topic}")
        else:
            log.info("ping sources - fails were published")
    else:
        log.info("ping sources - all success")


def publish_state(client: mqtt.Client, topic: str, obs_state: dict):
    """
    Publish obs current state to mqtt broker
    :param client: mqtt client
    :param topic: topic for obs state poll (like autostream/obs_state)
    :param obs_state:
            {
                "name": str (like 172.23.43.22:4455),
                "time": str (like %Y.%m.%d %H:%M:%S),
                "state": bool,
            }
    """
    msg = json.dumps(obs_state)
    result = client.publish(topic, msg)
    status = result[0]

    if status:
        log.warning(f"Failed to send message to topic {topic}")


def publish_ws(client: mqtt.Client, topic: str, data: dict):
    """
    Publish obsws request response to mqtt broker with quality of service = 2 - guarantee message sending ones
    :param client: mqtt client
    :param topic: topic for obsws request response (like autostream/)
    :param data:
            {
                "data": responseData / None,
                "error": None / "wrong password" / f"failed on remote command:{req}\nwith data:{data}"
            }
    """
    msg = json.dumps(data)
    result = client.publish(topic, msg, qos=2)
    status = result[0]

    if status:
        log.warning(f"Failed to send message to topic {topic}")
    else:
        log.info("obs websocket response for request published")


def on_message(client: mqtt.Client, userdata, msg):
    """
    Callback function for mqtt client, execute when message published to mqtt broker subscribed topic
    Gets obsws requests and sends responses by publish_ws() function
    obsws requests received in REQUEST_TOPIC related to this OBS_NAME (like autostream/request/172.34.5.20:4455)
    obsws responses published in RESPONSE_TOPIC related to this OBS_NAME (like autostream/response/172.34.5.20:4455)
     and commands response send in RESPONSE_TOPIC
    :param client: mqtt client
    :param userdata: ...
    :param msg: received message object

    request
    {
        "request": str (like "GetVersion"),
        "data": dict (like {"scene": scene_name})
        "password" = str
    }

    response {
                "obs_name": str (like 172.23.5.20:4455)
                "fails": {scene_name:[failed_source_name, ...], ...}
             }
    """

    request = json.loads(msg.payload)
    if msg.topic == REQUEST_TOPIC + "/" + OBS_NAME:
        log.info(f"OBWSW REQUEST:{request['request']}")
        publish_ws(client, RESPONSE_TOPIC + "/" + OBS_NAME,
                   run_obsws_request(request["request"], request["data"], request["password"]))


# get local variables
load_dotenv(WORK_DIRECTORY + ".env")
read_env()
# program can't execute while no necessary creds provided
if not(MQTT_USERNAME and MQTT_PASSWORD and OBSWS_PASSWORD):
    log.critical(f"environment variables are empty. Path to env-file: {WORK_DIRECTORY + '.env'}")
    exit("Error: .env file not found")
# program can't execute while no config.json file provided
if check_configure(WORK_DIRECTORY):
    read_configure()
else:
    log.critical(f"config.json not found. Path to config-file: {WORK_DIRECTORY + 'config.json'}")
    exit("Error: config.json not found")

# Get obs under control:
# 1. Check if obs is running before program was started
obs_pid = get_obs_pid()
# 2. Kill obs64.exe process and wait 5s until process will finish!
if obs_pid is not None:
    kill_process(obs_pid)
    log.info("obs was killed")
    time.sleep(5)

# 3. Start obs64.exe process as subprocess object
obs_process = start_obs_process(OBS_PATH)

# program can't execute while no obs64.exe process running
if not obs_process:
    log.critical("obs process was not created. Path to obs-file: " + OBS_PATH + "\\" + "obs64.exe")
    exit("Error: obs64.exe file not found")
else:
    log.info("obs was started")

# try to connect to obs by websockets and create obsws client; sleep 5s each try!; 5 tries
for _ in range(5):
    if check_obsws_connection_loop(OBSWS_HOST, OBSWS_PORT, OBSWS_PASSWORD):
        break
    log.error(f"obs websocket connection failed with host: {OBSWS_HOST}:{OBSWS_PORT}")
    time.sleep(2)
else:
    log.critical(f"obs websocket connection was not establish with host: {OBSWS_HOST}:{OBSWS_PORT}")
    exit("Error: no obs ws conn")

# try to connect to mqtt broker and create mqtt client
mqtt_client = create_mqtt_client(MQTT_USERNAME, MQTT_PASSWORD, MQTT_BROKER_HOST, MQTT_BROKER_PORT)
# program can't execute while no connection to mqtt broker
if mqtt_client is None:
    log.critical(f"Mqtt connection failed.\nMqtt broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    exit("Error: no mqtt conn")

if mqtt_client:
    # Asynchronously connection to allow background processing
    mqtt_client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_BROKER_KEEP_ALIVE_TIME)
    mqtt_client.loop_start()
    time_ping_count = 1
    while True:
        # sleep!
        time.sleep(UPDATE_LOOP_TIME)
        obs_state_msg = poll_process(obs_process)
        publish_state(mqtt_client, STATE_TOPIC, obs_state_msg)

        if not obs_state_msg["state"]:
            # try restart obs64.exe 3 times; each try sleep 1s
            try_count = 1
            log.info("obs restarting")
            obs_process = start_obs_process(OBS_PATH)

            while obs_process is None and try_count <= 3:
                # sleep !
                time.sleep(1)
                log.error(f"obs failed to restart. try: {try_count}")
                obs_process = start_obs_process(OBS_PATH)
                try_count += 1
        else:
            # ping sources ones in 20 UPDATE_LOOP_TIME's
            if time_ping_count % (UPDATE_LOOP_TIME * 60) == 0:
                try:
                    publish_ping_fail(mqtt_client, PING_TOPIC)
                except:
                    log.error("Failed to ping sources and publish")
                time_ping_count = 1
            else:
                time_ping_count += 1

complete_program()
