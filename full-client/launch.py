import sys
import os
from getpass import getpass
from dotenv import load_dotenv

PYTHON_PATH = sys.executable.rstrip("python.exe")
WORK_DIRECTORY = os.getcwd() + "\\"
load_dotenv()


def create_env_file(username, password):
    with open(".env", "w") as f:
        f.write("NAME=" + username + "\n")
        f.write("PASSWORD=" + password + "\n")


def info():
    mqtt_username = input("Input MQTT username:")
    mqtt_password = getpass("Input MQTT password:")
    if mqtt_username and mqtt_password:
        create_env_file(mqtt_username, mqtt_password)

    schedule_run_command = "schtasks /create /sc ONLOGON /tn Autostreaming /tr " + "\"" + PYTHON_PATH + "pythonw.exe " \
                           + WORK_DIRECTORY + "client.py" + "\""
    print("\nAutorun command for Autostreaming client app:")
    print(schedule_run_command)
    print("\nPython Path:")
    print(PYTHON_PATH)


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


def create_config_file():
    if not os.path.isfile("config.conf"):
        obs_path = find()
        with open("config.conf", "w") as f:
            f.write(obs_path)
    else:
        with open("config.conf") as f:
            obs_path = f.readline()

        if not os.path.isfile(obs_path + "\\" + "obs64.exe"):
            obs_path = find()
            with open("config.conf", "w") as f:
                f.write(obs_path)


def create_obs_script():
    username = str(os.getenv("NAME"))
    password = str(os.getenv("PASSWORD"))

    with open("obs_script_template") as t,\
            open("obs_script.py", "w") as f:
        for line in t:
            match line:
                case "# username =\n":
                    line = "username = \"" + username + "\"\n"
                case "# password =\n":
                    line = "password = \"" + password + "\"\n"
            f.write(line)


info()
create_config_file()
create_client_script()
# create obs_script.py file
if not os.path.isfile("obs_script.py"):
    create_obs_script()
