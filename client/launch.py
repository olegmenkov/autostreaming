"""
Script must be launched before client.py
Script gets all necessary creds and creates .env and config.json files
"""
import os
import sys
import subprocess
import time
from ctypes import windll
import asyncio
import json
from getpass import getpass
import paho.mqtt.client as mqtt
import simpleobsws


PYTHON_PATH = sys.executable.rstrip("python.exe")
WORK_DIRECTORY = os.getcwd() + "\\"


def get_drives() -> list:
    """:return list of Windows drives on current computer"""
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives


def check_obs_path(path: str) -> bool:
    """Check if obs64.exe exists in path"""
    return os.path.isfile(path + "\\" + "obs64.exe")


def get_obs_pid() -> int or None:
    """If obs is running return pid of obs64.exe process, if not then return None"""
    def obs_is_running(check_obs: list) -> bool:
        """9 - length of shell output if obs process was found"""
        return len(check_obs) == 9

    obs_pid = None
    shell_output = subprocess.check_output('tasklist /fi "IMAGENAME eq obs64.exe" /fo "CSV"').decode(
        encoding="windows-1251").replace('"', '').split(",")

    if obs_is_running(shell_output):
        obs_pid = int(shell_output[5])

    return obs_pid


def start_obs_process(obs_path: str) -> subprocess.Popen or None:
    """
    Start obs64.exe process
    :return process if success
    :return None if faild
    !!! obs_process.pid is pid of shell, no pid of obs64.exe
    """
    obs_process = None

    if check_obs_path(obs_path):
        obs_process = subprocess.Popen(obs_path + "\\" + "obs64.exe", cwd=obs_path)

    return obs_process


def check_configure(path: str) -> bool:
    """Check if config file exists"""
    return os.path.isfile(path + "config.json")


def check_mqtt_connection(username: str, password: str, host: str, port: int) -> bool:
    """
    Check if credentials for mqtt connection are correct
    Has sleep 0.5s!
    """
    client = mqtt.Client()
    client.username_pw_set(username, password)
    client.connect_async(host, port)
    client.loop_start()
    time.sleep(0.5)
    state = client.is_connected()
    client.loop_stop()

    if state:
        client.disconnect()

    return state


def create_obsws_client(host: str, port: int, password: str) -> simpleobsws.WebSocketClient:
    """:return: created from creds obsws object"""
    parameters = simpleobsws.IdentificationParameters(ignoreNonFatalRequestChecks=False)
    obs_ws_client = simpleobsws.WebSocketClient(url=f'ws://{host}:{port}', password=password,
                                                identification_parameters=parameters)
    return obs_ws_client


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


def create_env_file(mqtt_username: str, mqtt_password: str, obsws_password: str):
    """Create .env file with mqtt and obsws creds"""
    with open(".env", "w") as f:
        f.write("MQTT_USERNAME=" + mqtt_username + "\n")
        f.write("MQTT_PASSWORD=" + mqtt_password + "\n")
        f.write("OBSWS_PASSWORD=" + obsws_password + "\n")


def get_mqtt_creds() -> dict:
    """
    Requesting from the user in console mqtt creds
    :return:
    {
        "host": str,
        "port": int,
        "username": str,
        "password": str
    }
    """
    host = input("Input MQTT broker host (form: '0.0.0.0'): ")
    port = input("Input MQTT broker port: ")

    while not port.isnumeric():
        print("Port is incorrect!")
        port = input("Input MQTT broker port: ")

    port = int(port)
    username = input("Input MQTT username: ")
    password = getpass("Input MQTT password: ")

    while not check_mqtt_connection(username, password, host, port):
        print("Connection error! Check your information and try again.\n")

        host = input("Input MQTT broker host (form: '0.0.0.0'): ")
        port = input("Input MQTT broker port: ")

        while not port.isnumeric():
            print("Port is incorrect!")
            port = input("Input MQTT broker port: ")

        port = int(port)
        username = input("Input MQTT username:")
        password = getpass("Input MQTT password:")

    resp = {
        "host": host,
        "port": port,
        "username": username,
        "password": password
    }

    return resp


def get_obsws_creds() -> dict:
    """
    Requesting from the user in console obsws creds
    :return:
    {
        "host": str,
        "port": int,
        "password": str
    }
    """
    # Автоматическое определение и поддержание актуальным этих данных??
    host = input("Input OBS websocket host:")
    port = input("Input OBS websocket port:")

    while not port.isnumeric():
        print("Port is incorrect!")
        port = input("Input OBS websocket port:")

    port = int(port)

    password = getpass("Input OBS websocket password:")

    loop = asyncio.new_event_loop()

    while not loop.run_until_complete(check_obsws_connection(host, port, password)):
        print("Connection error! Check your information and try again.\n")
        host = input("Input OBS websocket host:")
        port = input("Input OBS websocket port:")

        while not port.isnumeric():
            print("Port is incorrect!")
            port = input("Input OBS websocket port:")

        port = int(port)
        password = getpass("Input OBS websocket password:")

    resp = {
        "host": host,
        "port": port,
        "password": password
    }

    return resp


def main(obs_path: str) -> dict:
    """
    Interact with user in console for getting mqtt and obsws creds;
    Give user command to launch in Windows Powershell with Administrator rights for restarting client.py
    when system reboot
    :param obs_path: path with obs64.exe file
    :return:
    {
        "mqtt: {
                    "host": str,
                    "port": int,
                    "username": str,
                    "password": str
                },
        "obsws":{
                    "host": str,
                    "port": int,
                    "password": str
                }
    }
    """
    mqtt_creds = get_mqtt_creds()

    if not get_obs_pid():
        start_obs_process(obs_path)
        time.sleep(1)

    obsws_creds = get_obsws_creds()

    schedule_run_command = "schtasks /create /sc ONLOGON /tn Autostreaming /tr " + "\"" + PYTHON_PATH + "pythonw.exe " \
                           + WORK_DIRECTORY + "client.py" + "\""

    print("\nAutorun command for Autostreaming client app:")
    print(schedule_run_command)
    print()

    resp = {
        "mqtt": mqtt_creds,
        "obsws": obsws_creds
    }

    return resp


def create_config(conf: dict):
    """Create configuration file"""
    with open("config.json", "w") as f:
        json.dump(conf, f)


def get_obs_path() -> str:
    """:return: path to obs64.exe in all Windows drives"""
    path = ""
    for drive in get_drives():
        for root, _, files in os.walk(f"{drive}:\\"):
            if "obs64.exe" in files:
                path = os.path.join(root)
                break
        if path:
            break
    return path


# if config file exists then open it, else create it
if check_configure(WORK_DIRECTORY):
    print("Reading configure...")
    with open(WORK_DIRECTORY + "config.json") as f:
        config = json.load(f)

    print("File was read successfully!")
else:
    print("Create configure file...")

    with open(WORK_DIRECTORY + "default_config.json") as f:
         default_config = json.load(f)

    config = default_config.copy()

print("Finding obs.exe file...")
obs_path = get_obs_path()

if obs_path:
    print("obs64.exe file was found!")
    config["obs_path"] = obs_path

    creds = main(obs_path)
    config["mqtt"]["host"] = creds["mqtt"]["host"]
    config["mqtt"]["port"] = creds["mqtt"]["port"]

    config["obsws"]["host"] = creds["obsws"]["host"]
    config["obsws"]["port"] = creds["obsws"]["port"]

    config["obs_name"] = creds["obsws"]["host"] + ":" + str(creds["obsws"]["port"])

    print("Writing information...")
    create_env_file(creds["mqtt"]["username"], creds["mqtt"]["password"], creds["obsws"]["password"])
    create_config(config)
    print("Files was created successfully!")
else:
    exit("Error: obs64.exe file was not found!")
