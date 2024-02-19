import os
from datetime import datetime
from typing import Any, List, Tuple

import simpleobsws
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import HTTPException
from loguru import logger

from db_class import Database


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


class Conductor:
    def __init__(self, db: Database):
        self.db = db

    async def ping_db(self):
        return await self.db.ping()

    async def create_user_in_db(self, user_id: str):
        try:
            await self.db.create_user_in_db(user_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def create_group_in_db(self, group_id: str):
        try:
            await self.db.create_group_in_db(group_id)
            logger.info(f'Added group {group_id} to database')
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def check_user_in_db(self, user_id: str):
        user_exists = await self.db.check_user_in_db(user_id)
        if not user_exists:
            raise HTTPException(status_code=401, detail='User unauthorized')

    async def check_group_in_db(self, group_id: str):
        group_exists = await self.db.check_group_in_db(group_id)
        if not group_exists:
            raise HTTPException(status_code=404, detail='Group not found')

    async def get_obs_info(self, user_id: str, obs_name: str):
        """
        Returns information about OBS stand by its owner and name.
        """
        await self.check_user_in_db(user_id)
        obs_info = await self.db.get_obs_info(user_id, obs_name)

        if not obs_info:
            raise HTTPException(status_code=404, detail='OBS with this name not found')

        ip, port, encrypted_password = obs_info
        password = decrypt_password(encrypted_password)
        return ip, port, password

    async def get_group_obs_info(self, group_id: str, obs_name: str):
        """
        Returns information about OBS stand by its owner and name.
        """
        await self.check_group_in_db(group_id)

        obs_info = await self.db.get_group_obs_info(group_id, obs_name)
        if not obs_info:
            raise HTTPException(status_code=404, detail='OBS with this name not found')

        ip, port, encrypted_password = obs_info
        password = decrypt_password(encrypted_password)

        return ip, port, password

    async def get_obs_client(self, user_id: str, obs_name: str):
        """
        Constructs obsclient for streaming for one of the user's stands.
        """
        ip, port, password = await self.get_obs_info(user_id, obs_name)
        parameters = simpleobsws.IdentificationParameters(
            ignoreNonFatalRequestChecks=False)
        obsclient = simpleobsws.WebSocketClient(
            url='ws://' + ip + ':' + port,
            password=password,
            identification_parameters=parameters)
        return obsclient

    async def get_group_obs_client(self, group_id: str, obs_name: str):
        """
        Constructs obsclient for streaming for one of the group's stands.
        """
        ip, port, password = await self.get_group_obs_info(group_id, obs_name)
        parameters = simpleobsws.IdentificationParameters(
            ignoreNonFatalRequestChecks=False)
        obsclient = simpleobsws.WebSocketClient(
            url='ws://' + ip + ':' + port,
            password=password,
            identification_parameters=parameters)
        return obsclient

    async def find_obs_groups(self, ip: str, port: str):
        """
        Находит группы, в которых есть OBS с таким ip и портом.
        """
        groups = await self.db.find_obs_groups(ip, port)
        return groups

    async def add_users_obs(self, user_id: str, obs_name: str, ip: str, port: str, password: str):
        """
        Adds OBS stand in db.
        """
        await self.check_user_in_db(user_id)
        encrypted_password = encrypt_password(password)
        await self.db.add_users_obs(user_id, obs_name, ip, port, encrypted_password)

    async def add_groups_obs(self, group_id: str, admin_id: str, obs_name: str):
        """
        Adds an OBS stand for a group in db and adds this stand for every group user.
        """
        await self.check_group_in_db(group_id)
        await self.check_user_in_db(admin_id)

        ip, port, password = await self.get_obs_info(admin_id, obs_name)
        encrypted_password = encrypt_password(password)  # Assuming encrypt_password is defined elsewhere

        try:
            await self.db.add_groups_obs(group_id, admin_id, obs_name, ip, port, encrypted_password)
        except HTTPException as e:
            raise e

        logger.info(f'Added OBS {obs_name} to group {group_id}')

        # Add OBS to all members of the group
        group_members = await self.db.get_group_members(group_id)  # Assuming this method exists
        for user_id in group_members:
            try:
                await self.add_users_obs(user_id, obs_name, ip, port, password)
                logger.info(f'Added OBS {obs_name} to user {user_id}')
            except Exception as err:
                logger.info(f'Failed to add OBS {obs_name} to user {user_id}: error {err}')

        return True

    async def add_groups_user(self, group_id: str, user_id: str, is_admin: bool):
        """
        Adds user in group.
        """
        await self.check_group_in_db(group_id)

        if await self.db.check_user_in_group(group_id, user_id):
            raise HTTPException(status_code=409, detail='Duplicated user.')

        await self.db.add_user_to_group(group_id, user_id, is_admin)

        # Check if the user exists, if not, create
        try:
            await self.check_user_in_db(user_id)
        except HTTPException:
            await self.create_user_in_db(user_id)

        # Add group OBS to the new user
        group_obs_names = await self.db.get_group_obs_names(group_id)
        for obs_name in group_obs_names:
            ip, port, password = await self.get_group_obs_info(group_id, obs_name)
            try:
                await self.add_users_obs(user_id, obs_name, ip, port, password)
            except Exception as err:
                pass

    async def del_group_user(self, group_id: str, user_id: str):
        """
        Удаляет пользователя из группы и групповые ОБС из его личных.
        """
        await self.check_user_in_db(user_id)
        await self.check_group_in_db(group_id)

        # Remove user from group
        await self.db.remove_user_from_group(group_id, user_id)
        logger.info(f'Removed user {user_id} from group {group_id}')

        # Remove admin status if user is an admin
        await self.db.remove_admin_from_group(group_id, user_id)

        # Remove group OBS from user's personal list
        await self.db.remove_group_obs_from_user(group_id, user_id)
        logger.info(f'Removed group OBS from user {user_id}')

    async def edit_users_obs(self, user_id: str, obs_name: str, field_to_change: str, new_value):
        """
        Edits OBS stand in the database.
        """
        await self.check_user_in_db(user_id)

        # Encrypt the password if the field being changed is 'password'
        if field_to_change == 'password':
            new_value = encrypt_password(new_value)  # Assuming encrypt_password is defined in Conductor

        try:
            await self.db.edit_users_obs(user_id, obs_name, field_to_change, new_value)
        except HTTPException as e:
            raise e
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    async def edit_groups_obs(self, group_id: str, obs_name: str, field_to_change: str, new_value):
        """
        Edits OBS stand in the database for a group.
        """
        await self.check_group_in_db(group_id)

        # Encrypt the password if the field being changed is 'password'
        if field_to_change == 'OBS_pswd':
            new_value = encrypt_password(new_value)

        try:
            await self.db.edit_groups_obs(group_id, obs_name, field_to_change, new_value)
        except HTTPException as e:
            raise e
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

        # Update OBS details for each user in the group
        group_members = await self.db.get_group_members(group_id)
        for user_id in group_members:
            try:
                await self.edit_users_obs(user_id, obs_name, field_to_change, new_value)
            except Exception as err:
                # Handle exception or log error
                pass

    async def raise_to_admin(self, user_id: str, group_id: str):
        """
        Adds user in group to the admin list.
        """
        await self.check_group_in_db(group_id)

        # Check if user is part of the group
        if not await self.db.check_user_in_group(group_id, user_id):
            raise HTTPException(status_code=404, detail=f'No such user in this group')

        # Check if user is already an admin
        if await self.db.is_user_admin_of_group(group_id, user_id):  # Assuming this method exists
            pass  # User is already an admin
        else:
            # Update user to admin
            await self.db.update_admin_status(group_id, user_id, True)

    async def remove_from_admins(self, user_id: str, group_id: str):
        """
        Removes user in group from the admin list.
        """
        await self.check_group_in_db(group_id)

        # Check if user is part of the group
        if not await self.db.check_user_in_group(group_id, user_id):
            raise HTTPException(status_code=404, detail=f'No such user in this group')

        # Check if user is already an admin
        if not await self.db.is_user_admin_of_group(group_id, user_id):  # Assuming this method exists
            pass  # User is not an admin, nothing to do
        else:
            # Update user to remove from admin
            await self.db.update_admin_status(group_id, user_id, False)

    async def del_users_obs(self, user_id: str, obs_name: str) -> str:
        """
        Deletes OBS stand from db for user by its obs_name.
        """
        await self.check_user_in_db(user_id)

        try:
            deleted_ip = await self.db.delete_users_obs(user_id, obs_name)
            return deleted_ip
        except HTTPException as e:
            raise e
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    async def del_groups_obs(self, group_id: str, obs_name: str) -> str:
        """
        Deletes OBS stand from db for group by its obs_name.
        """
        await self.check_group_in_db(group_id)

        try:
            deleted_obs_id = await self.db.delete_groups_obs(group_id, obs_name)
        except HTTPException as e:
            raise e

        # Remove this OBS from all non-admin users in the group
        group_members = await self.db.get_group_members(group_id)
        for user_id in group_members:
            if not await self.db.is_user_admin_of_group(group_id, user_id):
                try:
                    await self.db.remove_user_obs_by_id(user_id, deleted_obs_id)
                    logger.info(f"Deleted OBS {obs_name} from user {user_id}")
                except Exception as err:
                    logger.error(f"Error deleting OBS {obs_name} from user {user_id}: {err}")

        return deleted_obs_id

    async def get_users_obs(self, user_id: str) -> List[List[Any]]:
        """
        Returns all OBS stands (with ip and port) that are available for this user.
        """
        await self.check_user_in_db(user_id)

        try:
            obs_stands = await self.db.get_users_obs(user_id)
            return obs_stands
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    async def get_groups_obs(self, group_id: str) -> List[List[Any]]:
        """
        Returns all OBS stands (with ip and port) that are available for this group.
        """
        await self.check_group_in_db(group_id)

        try:
            obs_stands = await self.db.get_groups_obs(group_id)
            return obs_stands
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    async def create_planned_stream(self, user_id: str, obs_name: str, start_time: datetime, end_time: datetime):
        """
        This method checks if the new interval does not intersect with old intervals
        that have been already reserved. Then adds new interval in db and
        initiates scheduled function that invokes stream.
        """
        try:
            success = await self.db.create_planned_stream(user_id, obs_name, start_time, end_time)
            if not success:
                raise HTTPException(status_code=409, detail=f'Time slot conflict for OBS stand {obs_name}')
            return [start_time, end_time]
        except HTTPException as e:
            raise e
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    async def flush_old_intervals(self, obs_ip: str) -> None:
        """
        Deletes all intervals that end before time.now() for this IP.
        """
        try:
            await self.db.flush_old_intervals(obs_ip)
        except HTTPException as e:
            raise e
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    async def get_obs_intervals(self, user_id: str, obs_name: str) -> Tuple[List[Tuple[datetime, datetime]], str]:
        """
        Method that returns all intervals when the current OBS has already been reserved.
        """
        await self.check_user_in_db(user_id)

        try:
            intervals, obs_ip = await self.db.get_obs_intervals(user_id, obs_name)
            return intervals, obs_ip
        except HTTPException as e:
            raise e
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))
