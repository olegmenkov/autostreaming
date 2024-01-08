import pickle
from datetime import datetime
from typing import Any

import simpleobsws
from fastapi import HTTPException
from loguru import logger
from redis import ConnectionPool
from redis import Redis

from utils import intervals_intersection
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os


# 1 db - для юзеров и их стендов
# 2 db - для стендов и их времени использования

def encrypt_password(password):
    password = bytes(password, 'utf-8')
    load_dotenv()
    key = bytes(str(os.getenv('KEY')), 'utf-8')
    f = Fernet(key)
    return f.encrypt(password)


def decrypt_password(password):
    load_dotenv()
    key = bytes(str(os.getenv('KEY')), 'utf-8')
    f = Fernet(key)
    return f.decrypt(password).decode('utf-8')


class RedisDatabase:
    def __init__(self):
        self.pool = ConnectionPool(host='localhost', port=6379, db=0)
        self.db = Redis(connection_pool=self.pool)
        self.db.select(0)

        # если БД пустая, заводим таблицы пользователей и групп
        try:
            pickle.loads(self.db.get("users_table"))
        except Exception as err:
            self.db.set('users_table', pickle.dumps({}))

        try:
            pickle.loads(self.db.get("groups_table"))
        except Exception as err:
            self.db.set('groups_table', pickle.dumps({}))

    def ping_db(self):
        return self.db.ping()

    def show_bd(self):
        return pickle.loads(self.db.get("users_table"))

    def create_user_in_db(self, user_id: str):
        users_table = pickle.loads(self.db.get("users_table"))
        if user_id not in users_table:
            users_table[user_id] = {}
            self.db.set("users_table", pickle.dumps(users_table))

    def create_group_in_db(self, group_id: str):
        groups_table = pickle.loads(self.db.get("groups_table"))
        if group_id not in groups_table:
            groups_table[group_id] = {}
            groups_table[group_id]['admins'] = []
            groups_table[group_id]['chat_members'] = []
            groups_table[group_id]['obs'] = {}
            self.db.set("groups_table", pickle.dumps(groups_table))
            logger.info(f'Added group {group_id} to database')

        else:
            raise HTTPException(status_code=409,
                            detail=f'Duplicated group.')

    def check_user_in_db(self, user_id: str):
        users_table = pickle.loads(self.db.get("users_table"))
        if user_id not in users_table:
            raise HTTPException(status_code=401,
                                detail='User unauthorized')

    def check_group_in_db(self, group_id: str):
        groups_table = pickle.loads(self.db.get("groups_table"))

        if group_id not in groups_table:
            raise HTTPException(status_code=404,
                                detail='Group not found')

    def get_obs_info(self, user_id: str, obs_name: str) -> Any:
        """
        Returns information about obs stand by its owner and name
        """
        self.check_user_in_db(user_id)
        users_table = pickle.loads(self.db.get("users_table"))
        user_dict = users_table[user_id]
        if obs_name not in user_dict:
            raise HTTPException(status_code=404,
                                detail='Obs with this name not found')
        ip = user_dict[obs_name]['ip']
        port = user_dict[obs_name]['port']
        password = user_dict[obs_name]['password']

        password = decrypt_password(password)

        return ip, port, password

    def get_group_obs_info(self, group_id: str, obs_name: str) -> Any:
        """
        Returns information about obs stand by its owner and name
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        if obs_name not in group_dict["obs"]:
            raise HTTPException(status_code=404,
                                detail='Obs with this name not found')
        ip = group_dict["obs"][obs_name]['ip']
        port = group_dict["obs"][obs_name]['port']
        password = group_dict["obs"][obs_name]['password']

        password = decrypt_password(password)

        return ip, port, password

    def get_obs_client(self, user_id: str, obs_name: str) -> Any:
        """
        Constructs obsclient for streaming for one of the users stand
        """
        ip, port, password = self.get_obs_info(user_id, obs_name)
        parameters = simpleobsws.IdentificationParameters(
            ignoreNonFatalRequestChecks=False)
        obsclient = simpleobsws.WebSocketClient(
            url='ws://' + ip + ':' + port,
            password=password,
            identification_parameters=parameters)
        return obsclient

    def get_group_obs_client(self, group_id: str, obs_name: str) -> Any:
        """
        Constructs obsclient for streaming for one of the groups stand
        """
        ip, port, password = self.get_obs_info(group_id, obs_name)
        parameters = simpleobsws.IdentificationParameters(
            ignoreNonFatalRequestChecks=False)
        obsclient = simpleobsws.WebSocketClient(
            url='ws://' + ip + ':' + port,
            password=password,
            identification_parameters=parameters)
        return obsclient

    def find_obs_groups(self, ip: str, port: str):
        """
        Находит группы, в которых есть OBS с таким ip и портом
        """
        groups = []
        groups_table = pickle.loads(self.db.get("groups_table"))
        for group_id, group_dict in groups_table.items():
            for obs_name in group_dict['obs']:
                if group_dict['obs'][obs_name]["ip"] == ip and group_dict['obs'][obs_name]["port"] == port:
                    groups.append(group_id)

        return groups

    def add_users_obs(self, user_id: str, obs_name: str, ip: str,
                      port: str, password: str) -> None:
        """
        Adds stand in db
        """
        self.check_user_in_db(user_id)
        users_table = pickle.loads(self.db.get("users_table"))
        user_dict = users_table[user_id]
        for name, data in user_dict.items():
            if (ip == data['ip'] and port == data['port']) or obs_name == name: # если уже есть стенд с таким [ip и портом] или именем
                raise HTTPException(status_code=409,
                                    detail=f'Duplicated stand. Stand {name}'
                                           f' already with ip {ip} and port {port}')
        password = encrypt_password(password)

        user_dict[obs_name] = {"ip": ip, "port": port, "password": password}
        users_table[user_id] = user_dict
        self.db.set("users_table", pickle.dumps(users_table))

    def add_groups_obs(self, group_id: str, admin_id: str, obs_name: str) -> bool:
        """
        Adds stand for a group in db and adds this stand for every group user
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]

        self.check_user_in_db(admin_id)
        users_table = pickle.loads(self.db.get("users_table"))
        user_dict = users_table[admin_id]

        ip, port, password = self.get_obs_info(admin_id, obs_name)
        for name, data in group_dict["obs"].items():
            # если уже есть стенд с таким [ip и портом] или именем
            if (ip == data['ip'] and port == data['port']) or obs_name == name:
                raise HTTPException(status_code=409,
                                    detail=f'Duplicated stand. Stand {name}'
                                           f' already with ip {ip} and port {port}')
        if obs_name not in user_dict:
            logger.info(f"Didn't find obs {obs_name} in admin {admin_id} list {user_dict}")
            return False
        elif obs_name in group_dict["obs"]:
            logger.info(f"Obs {obs_name} is already in the group")
            return False
        else:
            group_dict["obs"][obs_name] = {"ip": user_dict[obs_name]["ip"], "port": user_dict[obs_name]["port"], "password": user_dict[obs_name]["password"]}

            groups_table[group_id] = group_dict
            self.db.set("groups_table", pickle.dumps(groups_table))

            logger.info(f'Added obs {obs_name} to group {group_id}')

            # теперь добавим эту ОБС всем членам группы
            for user_id in group_dict["chat_members"]:
                users_table = pickle.loads(self.db.get("users_table"))
                user_dict = users_table[user_id]
                try:
                    self.add_users_obs(user_id, obs_name, ip, port, password)
                    logger.info(f'Added obs {obs_name} to user {user_id}')
                except Exception as err:
                    logger.info(f'Failed to add obs {obs_name} to user {user_id}: error {err}')

            return True

    def add_groups_user(self, group_id: str, user_id: str, is_admin: bool) -> None:
        """
        Adds user in group
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        for existing_user_id in group_dict['chat_members']:
            if existing_user_id == user_id:
                raise HTTPException(status_code=409,
                                    detail=f'Duplicated user.')
        group_dict['chat_members'].append(user_id)
        if is_admin:
            group_dict['admins'].append(user_id)
        groups_table[group_id] = group_dict
        self.db.set("groups_table", pickle.dumps(groups_table))

        # если участника группы ещё нет в БД в качестве пользователя, добавляем его
        users_table = pickle.loads(self.db.get("users_table"))
        if user_id not in users_table:
            self.create_user_in_db(user_id)

        # Добавляем новому участнику ОБС группы, которых у него ещё нет
        for obs_name in group_dict['obs']:
            ip, port, password = self.get_group_obs_info(group_id, obs_name)
            try:
                self.add_users_obs(user_id, obs_name, ip, port, password)
            except Exception as err:
                pass


    def del_group_user(self, group_id: str, user_id: str):
        """
        Удаляет пользователя из группы и групповые ОБС из его личных
        """

        # Удаляем участника из группы
        self.check_user_in_db(user_id)
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        logger.info(f'removing user {user_id}')
        group_dict['chat_members'].remove(user_id)

        # Админов просто удаляем из списка
        if user_id in group_dict['admins']:
            group_dict['admins'].remove(user_id)
            logger.info(f"Deleted user {user_id} from group {group_id}")

        # У обычных пользователей удаляем групповые ОБС из доступных по ip и порту (юзер мог переименовать их у себя)
        elif user_id not in group_dict['admins']:
            users_table = pickle.loads(self.db.get("users_table"))
            user_dict = users_table[user_id]
            for group_obs_name in group_dict["obs"]:
                group_obs_ip, group_obs_port, pswd = self.get_group_obs_info(group_id, group_obs_name)
                to_delete = []
                for user_obs_name in user_dict:
                    if group_obs_ip == user_dict[user_obs_name]["ip"] and group_obs_port == \
                            user_dict[user_obs_name]["port"]:
                        to_delete.append(user_obs_name)
                for name in to_delete:
                    user_dict.pop(name)
                    logger.info(f"Deleted obs {name}({user_obs_name}) from user {user_id}")

        users_table[user_id] = user_dict
        self.db.set("users_table", pickle.dumps(users_table))
        logger.info(f'users table: {users_table}')

        groups_table[group_id] = group_dict
        self.db.set("groups_table", pickle.dumps(groups_table))

    def edit_users_obs(self, user_id: str, obs_name: str, field_to_change: str, new_value) -> None:
        """
        Edits stand in db
        """
        self.check_user_in_db(user_id)
        users_table = pickle.loads(self.db.get("users_table"))
        user_dict = users_table[user_id]
        if obs_name not in user_dict:
            raise HTTPException(status_code=404,
                                detail='Obs with this name not found')
        if field_to_change == 'obs_name':
            obs_info = user_dict[obs_name]  # ip, port, paswd без изменений
            popped = user_dict.pop(obs_name)
            user_dict[new_value] = obs_info   # добавляем ту же ОБС под новым именем
            users_table[user_id] = user_dict
            self.db.set("users_table", pickle.dumps(users_table))
        elif field_to_change in {'ip', 'port', 'password'}:
            if field_to_change == 'password':
                new_value = encrypt_password(new_value)
            user_dict[obs_name][field_to_change] = new_value
            users_table[user_id] = user_dict
            self.db.set("users_table", pickle.dumps(users_table))
        else:
            raise HTTPException(status_code=400,
                                detail=f'No such field as {field_to_change}')

    def edit_groups_obs(self, group_id: str, obs_name: str, field_to_change: str, new_value) -> None:
        """
        Edits stand in db
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        if obs_name not in group_dict['obs']:
            raise HTTPException(status_code=404,
                                detail='Obs with this name not found')
        if field_to_change == 'obs_name':
            obs_info = group_dict['obs'][obs_name]  # ip, port, paswd без изменений
            popped = group_dict['obs'].pop(obs_name)
            group_dict['obs'][new_value] = obs_info   # добавляем ту же ОБС под новым именем
            groups_table[group_id] = group_dict
            self.db.set("groups_table", pickle.dumps(groups_table))
        elif field_to_change in {'ip', 'port', 'password'}:
            if field_to_change == 'password':
                new_value = encrypt_password(new_value)
            group_dict['obs'][obs_name][field_to_change] = new_value
            groups_table[group_id] = group_dict
            self.db.set("groups_table", pickle.dumps(groups_table))

        else:
            raise HTTPException(status_code=400,
                                detail=f'No such field as {field_to_change}')
        # Дальше меняем эти OBS и в личных OBS пользователей
        for user_id in groups_table[group_id]["chat_members"]:
            try:
                self.edit_users_obs(user_id, obs_name, field_to_change, new_value)
            except Exception as err:
                pass

    def raise_to_admin(self, user_id: str, group_id: str):
        """
        Adds user in group to the admin list
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        if user_id not in group_dict["chat_members"]:
            raise HTTPException(status_code=404,
                                detail=f'No such user in this group')
        elif user_id in group_dict["admins"]:
            pass
        else:
            group_dict["admins"].append(user_id)

    def remove_from_admins(self, user_id: str, group_id: str):
        """
        Removes user in group from the admin list
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        if user_id not in group_dict["chat_members"]:
            raise HTTPException(status_code=404,
                                detail=f'No such user in this group')
        elif user_id not in group_dict["admins"]:
            pass
        else:
            group_dict["admins"].remove(user_id)

    def del_users_obs(self, user_id: str, obs_name: str) -> str:
        """
        Deletes obs stand from db for user by its obs_name
        """
        self.check_user_in_db(user_id)
        users_table = pickle.loads(self.db.get("users_table"))
        user_dict = users_table[user_id]
        if obs_name not in user_dict:
            raise HTTPException(status_code=404,
                                detail='Obs with this name not found')
        deleted = user_dict.pop(obs_name)
        users_table[user_id] = user_dict
        self.db.set("users_table", pickle.dumps(users_table))
        return deleted['ip']

    def del_groups_obs(self, group_id: str, obs_name: str) -> str:
        """
        Deletes obs stand from db for group by its obs_name
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        if obs_name not in group_dict['obs']:
            logger.debug(f'Obs with this name not found in {group_dict["obs"]}')
            raise HTTPException(status_code=404,
                                detail=f'Obs with this name not found in {group_dict["obs"]}')

        # Удаляем эту OBS у всех пользователей, кроме админов (по айпи и порту)
        for user_id in group_dict["chat_members"]:
            if user_id not in group_dict['admins']:
                users_table = pickle.loads(self.db.get("users_table"))
                user_dict = users_table[user_id]
                group_obs_ip, group_obs_port, group_obs_password = self.get_group_obs_info(group_id, obs_name)
                to_delete = []
                for user_obs_name in user_dict:
                    if group_obs_ip == user_dict[user_obs_name]["ip"] and group_obs_port == \
                            user_dict[user_obs_name]["port"]:
                        to_delete.append(user_obs_name)
                for name in to_delete:
                    user_dict.pop(name)
                    logger.info(f"Deleted obs {obs_name}({user_obs_name}) from user {user_id}")
                self.db.set("users_table", pickle.dumps(users_table))

        deleted = group_dict['obs'].pop(obs_name)
        groups_table[group_id] = group_dict
        self.db.set("groups_table", pickle.dumps(groups_table))


    def get_users_obs(self, user_id: str) -> list[list[Any]]:
        """
        Returns all obs stands (with ip and port) that available for this user
        i.e. added before
        """
        self.check_user_in_db(user_id)
        users_table = pickle.loads(self.db.get("users_table"))
        user_dict = users_table[user_id]
        obs_names = [[name, info['ip'], info['port'], ] for name, info in
                     user_dict.items()]
        return obs_names

    def get_groups_obs(self, group_id: str) -> list[list[Any]]:
        """
        Returns all obs stands (with ip and port) that available for this group
        i.e. added before
        """
        self.check_group_in_db(group_id)
        groups_table = pickle.loads(self.db.get("groups_table"))
        group_dict = groups_table[group_id]
        obs_names = [[name, info['ip'], info['port'], ] for name, info in
                     group_dict['obs'].items()]

        return obs_names

    def create_planned_stream(self, user_id: str, key: str,
                              date1: datetime, date2: datetime, obs_name: str):
        """
        This method checks if new interval not intersects with old intervals
        that have been already reserved. Then add new interval in db and
        initiate scheduled function that invokes stream.
        """
        obs_intervals, obs_ip = self.get_obs_intervals(user_id, obs_name)
        flag, interval = intervals_intersection(obs_intervals, [date1, date2])
        if not flag:
            raise HTTPException(status_code=409,
                                detail=f'Obs stand with this ip already in use'
                                       f' (working interval from {interval[0]}'
                                       f' to {interval[1]}')
        obs_intervals.append([date1, date2])
        self.db.select(1)
        self.db.set(obs_ip, pickle.dumps(
            obs_intervals))  # todo: добавить экспаир через неделю
        self.db.select(0)

        return interval

    def flush_old_intervals(self, obs_ip: str) -> None:
        """
        Deletes all intervals that end before time.now() for this ip
        """
        self.db.select(1)
        obs_intervals = pickle.loads(self.db.get(obs_ip))
        self.db.select(0)
        obs_intervals = [interval for interval in obs_intervals if
                         interval[1] > datetime.now()]
        self.db.select(1)
        self.db.set(obs_ip, pickle.dumps(obs_intervals))
        self.db.select(0)

    def get_obs_intervals(self, user_id: str,
                          obs_name: str) -> tuple[list, str]:
        """
        Method that returns all intervals when current obs has already reserved
        """
        self.check_user_in_db(user_id)
        user_dict = pickle.loads(self.db.get(user_id))
        if obs_name not in user_dict:
            raise HTTPException(status_code=404,
                                detail='Obs with this name not found')
        obs_ip = user_dict[obs_name]["ip"]
        self.db.select(1)
        raw_obs = self.db.get(obs_ip)
        self.db.select(0)
        if raw_obs is None:
            obs_intervals = []
        else:
            obs_intervals = pickle.loads(raw_obs)

        obs_intervals = obs_intervals if obs_intervals else []
        return obs_intervals, obs_ip
