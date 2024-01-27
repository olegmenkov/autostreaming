import json
import sys
import os
import time
from getpass import getpass
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from obswebsocket import obsws, exceptions

PYTHON_PATH = sys.executable.rstrip("python.exe")
WORK_DIRECTORY = os.getcwd() + "\\"

config = {"mqtt_broker_host": "172.18.130.40", "mqtt_broker_port": 1883, "mqtt_broker_keep_alive_time": 60,
          "update_loop_time": 1}
load_dotenv()


def check_mqtt_connection(username, password):
    client = mqtt.Client()
    client.username_pw_set(username, password)
    client.connect_async(config["mqtt_broker_host"], config["mqtt_broker_port"], config["mqtt_broker_keep_alive_time"])
    client.loop_start()
    time.sleep(0.5)
    state = client.is_connected()
    client.loop_stop()

    if state:
        client.disconnect()

    return state


def check_obsws_connection(host, port, password):
    obs = obsws(host, port, password)
    try:
        obs.connect()
    except exceptions.ConnectionFailure:
        return False
    else:
        return True


def create_env_file(mqtt_username, mqtt_password, obsws_password):
    with open(".env", "w") as f:
        f.write("MQTT_USERNAME=" + mqtt_username + "\n")
        f.write("MQTT_PASSWORD=" + mqtt_password + "\n")
        f.write("OBSWS_PASSWORD=" + obsws_password + "\n")


def start():
    mqtt_username = input("Input MQTT username:")
    mqtt_password = getpass("Input MQTT password:")

    while not check_mqtt_connection(mqtt_username, mqtt_password):
        print("Connection error! Check your information and try again.\n")
        mqtt_username = input("Input MQTT username:")
        mqtt_password = getpass("Input MQTT password:")

    obsws_host = input("Input OBS websocket host:")
    obsws_port = input("Input OBS websocket port:")
    obsws_password = getpass("Input OBS websocket password:")

    while not check_obsws_connection(obsws_host, obsws_port, obsws_password):
        print("Connection error! Check your information and try again.\n")
        obsws_host = input("Input OBS websocket host:")
        obsws_port = input("Input OBS websocket port:")
        obsws_password = getpass("Input OBS websocket password:")

    config.update({"obsws_host": obsws_host, "obsws_port": obsws_port})
    create_env_file(mqtt_username, mqtt_password, obsws_password)

    schedule_run_command = "schtasks /create /sc ONLOGON /tn Autostreaming /tr " + "\"" + PYTHON_PATH + "pythonw.exe " \
                           + WORK_DIRECTORY + "client.py" + "\""
    print("\nAutorun command for Autostreaming client app:")
    print(schedule_run_command)


def test():
    mqtt_username = "recorder"
    mqtt_password = "recorder2020"
    obsws_host = "localhost"
    obsws_port = 4455
    obsws_password = "KERA3InQESizeUSa"
    config.update({"obsws_host": obsws_host, "obsws_port": obsws_port})
    create_env_file(mqtt_username, mqtt_password, obsws_password)

    schedule_run_command = "schtasks /create /sc ONLOGON /tn Autostreaming /tr " + "\"" + PYTHON_PATH + "pythonw.exe " \
                           + WORK_DIRECTORY + "client.py" + "\""
    print("\nAutorun command for Autostreaming client app:")
    print(schedule_run_command)


def create_client_script():
    with open("client_template") as t,\
            open("client.py", "w") as f:
        for line in t:
            if line == "# WORK_DIRECTORY =\n":
                line = "WORK_DIRECTORY = \"" + WORK_DIRECTORY + "\\" + "\"\n"
            f.write(line)


# find path to obs64.exe in disk C:\
def find():
    for root, _, files in os.walk("C:\\"):
        if "obs64.exe" in files:
            return os.path.join(root)

    return None


def create_config():
    obs_path = find()
    config.update({"obs_path": obs_path})

    with open("config.json", "w") as f:
        json.dump(config, f)


start()
# test()
create_config()
create_client_script()
