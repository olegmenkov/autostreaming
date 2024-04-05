import json
import uuid
from datetime import datetime

from fastapi import HTTPException
from typing import Tuple, Union, List, Any

from sqlalchemy import text, TextClause
from sqlalchemy.ext.asyncio import create_async_engine


class Database:
    """
    A class for managing asynchronous connections to a database.
    It initializes with parameters required for connecting to the database.
    """

    def __init__(self, host, port, user, password, database):
        """
          Initializes a new instance of the Database class.

          Args:
              host (str): The database server host.
              port (int): The port number on which the database server is running.
              user (str): The username used for authentication with the database.
              password (str): The password used for authentication with the database.
              database (str): The name of the database to connect to.

          This method constructs a database URL and initializes an asynchronous engine for database connections.
          """
        self._database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        self._engine = create_async_engine(self._database_url, echo=True)

    async def execute(self, query: Union[str, TextClause], *args, **kwargs):
        """
        Executes an SQL query asynchronously using the database engine.

        Args:
            query (str): The SQL query to be executed.
            *args: Positional arguments to be passed to the query.
            **kwargs: Keyword arguments to be passed to the query.

        Returns:
            The result of the executed query. The exact type of the result depends on the nature of the SQL query.

        This method provides a generic interface for executing various types of SQL queries. It opens an asynchronous
        connection with the database, executes the provided query, and returns the result. This method is suitable
        for executing queries that modify the database as well as for fetching data.
        """
        async with self._engine.begin() as conn:
            result = await conn.execute(query, *args, **kwargs)
            return result

    async def close(self):
        """
        Asynchronously disposes of the database engine resources.

        This method should be called when the database connections are no longer needed. It ensures that all
        connections are properly closed and the resources associated with the database engine are released.

        It's particularly important to call this method in applications that create and dispose of database
        connections frequently or have long-running processes to prevent resource leaks.
        """
        await self._engine.dispose()

    async def create_user_in_db(self, user_id: str):
        query = text("""
            INSERT INTO users ("U_id")
            VALUES (:user_id)
                """)
        await self.execute(query, {'user_id': user_id})

    async def ping(self):
        query = text("""SELECT 1""")
        await self.execute(query)

    async def create_group_in_db(self, group_id: str):
        query = text("""
            INSERT INTO groups ("G_id")
            VALUES (:group_id)
        """)
        await self.execute(query, {'group_id': group_id})

    async def check_user_in_db(self, user_id: str) -> bool:
        query = text('SELECT EXISTS(SELECT 1 FROM users WHERE "U_id" = :user_id)')
        result = await self.execute(query, {'user_id': user_id})
        return result.scalar()

    async def check_group_in_db(self, group_id: str) -> bool:
        query = text("""SELECT 1
        FROM groups
        WHERE "G_id" = :group_id""")
        result = await self.execute(query, {'group_id': group_id})
        return result.scalar()

    async def get_obs_info(self, user_id: str, obs_name: str):
        query = text("""
            SELECT "OBS_ip", "OBS_port", "OBS_pswd" 
            FROM obs INNER JOIN users_obs USING("OBS_id")
            WHERE user_id = :user_id AND "UO_name" = :obs_name
        """)
        result = await self.execute(query, {'user_id': int(user_id), 'obs_name': obs_name})
        return result.fetchone()

    async def get_group_obs_info(self, group_id: str, obs_name: str):
        query = text("""
            SELECT ip, port, password 
            FROM groups_obs INNER JOIN obs USING("OBS_id")
            WHERE group_id = :group_id AND "GO_name" = :obs_name
        """)
        result = await self.execute(query, {'group_id': group_id, 'obs_name': obs_name})
        return await result.fetchone()

    async def find_obs_groups(self, ip: str, port: str):
        query = text("""
            SELECT group_id 
            FROM groups_obs WHERE "OBS_id" = (
                SELECT "OBS_id" from obs WHERE "OBS_ip" = :ip AND "OBS_port" = :port LIMIT 1);
        """)
        result = await self.execute(query, {'ip': ip, 'port': int(port)})
        rows = result.fetchall()
        return [row[0] for row in rows]

    async def add_users_obs(self, user_id: str, obs_name: str, ip: str, port: str, encrypted_password: str):
        # Check for duplicates
        check_query = text("""
            SELECT 1
            FROM users_obs us INNER JOIN obs ob ON ob."OBS_id" = us."OBS_id"
            WHERE us.user_id = :user_id AND (us."UO_name" = :obs_name OR (ob."OBS_ip" = :ip AND ob."OBS_port" = :port))
        """)
        result = await self.execute(check_query, {'user_id': int(user_id), 'obs_name': obs_name, 'ip': ip, 'port': int(port)})
        exists = result.scalar()

        if exists:
            raise HTTPException(status_code=409, detail=f'Duplicated stand. Stand with ip {ip} and port {port} or name {obs_name} already exists')

        obs_id = uuid.uuid4()
        # Insert new OBS info
        insert_query = text("""
            INSERT INTO users_obs (user_id, "OBS_id", "UO_name", "UO_access_grant") 
            VALUES (:user_id, :obs_id, :obs_name, :grant);
        """)
        await self.execute(insert_query, {'user_id': int(user_id), 'obs_id': str(obs_id), 'obs_name': obs_name, 'grant': True})
        # Insert new OBS info
        insert_query = text("""
            INSERT INTO obs ("OBS_id", "OBS_ip", "OBS_port", "OBS_pswd")
            VALUES (:obs_id, :ip, :port, :encrypted_password);
        """)
        await self.execute(insert_query, {'obs_id': str(obs_id), 'ip': ip, 'port': int(port), 'encrypted_password': encrypted_password})


    async def add_groups_obs(self, group_id: str, admin_id: str, obs_name: str, ip: str, port: str, encrypted_password: str):
        # Check for duplicate OBS in the group
        check_group_obs_query = text("""
            SELECT 1 FROM groups_obs INNER JOIN obs USING("OBS_id")
            WHERE group_id = :group_id AND
            ("GO_name" = :obs_name OR ("OBS_ip" = :ip AND "OBS_port" = :port))
        """)
        result = await self.execute(check_group_obs_query, {'group_id': group_id,
                                                            'obs_name': obs_name,
                                                            'ip': ip, 'port': int(port)})
        if result.scalar():
            raise HTTPException(status_code=409, detail=f'Duplicated OBS in group.')

        find_obs_id_query = text(f"""
        SELECT "OBS_id" from obs 
        WHERE "OBS_ip" = :ip AND "OBS_port" = :port
        LIMIT 1;
        """)
        result = await self.execute(find_obs_id_query, {'ip': ip, 'port': int(port)})
        if not result.scalar():
            raise HTTPException(status_code=404, detail=f'OBS with ip {ip} and port {port} not found.')

        for row in result:
            obs_id = row[0]
            break

        # Insert OBS into group_obs_info
        insert_group_obs_query = text("""
            INSERT INTO groups_obs (group_id, "OBS_id", "GO_name") 
            VALUES (:group_id, :obs_id, :obs_name)
        """)
        await self.execute(insert_group_obs_query, {'group_id': group_id, 'obs_id': obs_id, 'obs_name': obs_name})
        insert_group_obs_query = text("""
                    INSERT INTO obs ("OBS_id", "OBS_ip", "OBS_port", "OBS_pswd") 
                    VALUES (:obs_id, :ip, :port, :encrypted_password)
                """)
        await self.execute(insert_group_obs_query, {'obs_id': obs_id, 'ip': ip, 'port': port,
                                                    'encrypted_password': encrypted_password})

    async def check_user_in_group(self, group_id: str, user_id: str) -> bool:
        query = text("""
            SELECT user_id FROM group_membership 
            WHERE group_id = :group_id AND user_id = :user_id
        """)
        result = await self.execute(query, {'group_id': group_id, 'user_id': int(user_id)})
        return bool(result.scalar())

    async def add_user_to_group(self, group_id: str, user_id: str, is_admin: bool):
        query = text("""
            INSERT INTO group_membership (group_id, user_id, "M_admin") 
            VALUES (:group_id, :user_id, :is_admin)
            ON CONFLICT (group_id, user_id) DO NOTHING
        """)
        await self.execute(query, {'group_id': group_id,
                                   'user_id': int(user_id), 'is_admin': is_admin})

    async def get_group_obs_names(self, group_id: str):
        query = text("""
            SELECT "GO_name" FROM groups_obs 
            WHERE group_id = :group_id
        """)
        result = await self.execute(query, {'group_id': group_id})
        return [row[0] for row in result.fetchall()]

    async def remove_user_from_group(self, group_id: str, user_id: str):
        query = text("""
            DELETE FROM group_membership 
            WHERE group_id = :group_id AND user_id = :user_id
        """)
        await self.execute(query, {'group_id': group_id, 'user_id': int(user_id)})

    async def remove_admin_from_group(self, group_id: str, user_id: str):
        query = text("""
            UPDATE group_membership 
            SET "M_admin" = False 
            WHERE group_id = :group_id AND user_id = :user_id
        """)
        await self.execute(query, {'group_id': group_id, 'user_id': int(user_id)})

    async def remove_group_obs_from_user(self, group_id: str, user_id: str):
        query = text("""
            DELETE FROM users_obs 
            WHERE user_id = :user_id AND "UO_name" IN (
                SELECT "GO_name" FROM groups_obs WHERE group_id = :group_id
            )
        """)
        await self.execute(query, {'group_id': group_id, 'user_id': int(user_id)})

    async def edit_users_obs(self, user_id: str, obs_name: str, field_to_change: str, new_value):
        # Handle updating OBS name separately
        if field_to_change == 'obs_name':
            query = text("""
                UPDATE users_obs 
                SET "UO_name" = :new_value 
                WHERE user_id = :user_id AND "UO_name" = :obs_name
            """)
            await self.execute(query, {'user_id': int(user_id), 'obs_name': obs_name, 'new_value': new_value})
        elif field_to_change in {'ip', 'port', 'password'}:
            field_in_db_mapping = {'ip': "OBS_ip", 'port': "OBS_port", 'password': "OBS_pswd"}
            field_in_db = field_in_db_mapping[field_to_change]
            if field_to_change == "port":
                new_value = int(new_value)
            # Update other fields directly
            query = text(f"""
            WITH temp as (SELECT "OBS_id" FROM users_obs WHERE user_id = :user_id AND "UO_name" = :obs_name)
                UPDATE obs 
                SET "{field_in_db}" = :new_value 
                WHERE "OBS_id" IN (SELECT "OBS_id" FROM temp);
            """)
            await self.execute(query, {'user_id': int(user_id), 'obs_name': obs_name, 'new_value': new_value})
        else:
            raise HTTPException(status_code=400, detail=f'No such field as {field_to_change}')

    async def edit_groups_obs(self, group_id: str, obs_name: str, field_to_change: str, new_value):
        if field_to_change == 'obs_name':
            query = text("""
                UPDATE groups_obs 
                SET "GO_name" = :new_value 
                WHERE group_id = :group_id AND "GO_name" = :obs_name
            """)
            await self.execute(query, {'group_id': group_id, 'obs_name': obs_name, 'new_value': new_value})
        elif field_to_change in {'ip', 'port', 'password'}:
            field_in_db_mapping = {'ip': "OBS_ip", 'port': "OBS_port", 'password': "OBS_pswd"}
            field_in_db = field_in_db_mapping[field_to_change]
            if field_to_change == "port":
                new_value = int(new_value)
            obs_id_subquery = text("""
                SELECT "OBS_id" FROM groups_obs 
                WHERE group_id = :group_id AND "GO_name" = :obs_name
            """)
            obs_id_result = await self.execute(obs_id_subquery, {'group_id': group_id, 'obs_name': obs_name})
            obs_id = obs_id_result.scalar()

            if obs_id:
                update_query = text(f"""
                    UPDATE obs 
                    SET "{field_in_db}" = :new_value 
                    WHERE "OBS_id" = :obs_id
                """)
                await self.execute(update_query, {'obs_id': obs_id, 'new_value': new_value})
        else:
            raise HTTPException(status_code=400, detail=f'No such field as {field_to_change}')

    async def get_group_members(self, group_id: str):
        query = text("""
            SELECT user_id FROM group_membership 
            WHERE group_id = :group_id
        """)
        result = await self.execute(query, {'group_id': group_id})
        return [row[0] for row in result.fetchall()]

    async def update_admin_status(self, group_id: str, user_id: str, admin_status: bool):
        query = text("""
            UPDATE group_membership
            SET M_admin = :admin_status
            WHERE group_id = :group_id AND user_id = :user_id
        """)
        await self.execute(query, {'group_id': group_id, 'user_id': user_id, 'admin_status': admin_status})

    async def is_user_admin_of_group(self, group_id: str, user_id: str) -> bool:
        query = text("""
            SELECT "M_admin" FROM group_membership
            WHERE group_id = :group_id AND user_id = :user_id
        """)
        result = await self.execute(query, {'group_id': group_id, 'user_id': int(user_id)})
        row = result.fetchone()
        return row is not None and row[0]  # row[0] is the M_admin value

    async def delete_users_obs(self, user_id: str, obs_name: str) -> str:
        # First, get the IP of the OBS to be deleted for return value
        get_ip_query = text("""
            SELECT obs."OBS_ip", obs."OBS_id"
            FROM users_obs INNER JOIN obs ON users_obs."OBS_id" = obs."OBS_id"
            WHERE user_id = :user_id AND "UO_name" = :obs_name
        """)
        result = await self.execute(get_ip_query, {'user_id': int(user_id), 'obs_name': obs_name})
        res = result.fetchall()
        if not res:
            raise HTTPException(status_code=404, detail='OBS with this name not found')
        obs_ip, obs_id = res[0]

        # Delete the OBS stand
        delete_query = text("""
            DELETE FROM users_obs 
            WHERE user_id = :user_id AND "UO_name" = :obs_name
        """)
        await self.execute(delete_query, {'user_id': int(user_id), 'obs_name': obs_name})

        return obs_ip

    async def delete_groups_obs(self, group_id: str, obs_name: str) -> str:
        # Get the OBS ID to be deleted for return value
        get_obs_id_query = text("""
            SELECT "OBS_id" FROM groups_obs
            WHERE group_id = :group_id AND "GO_name" = :obs_name
        """)
        result = await self.execute(get_obs_id_query, {'group_id': group_id, 'obs_name': obs_name})
        obs_id = result.scalar()

        if not obs_id:
            raise HTTPException(status_code=404, detail='OBS with this name not found in group')

        # Delete the OBS stand
        delete_query = text("""
            DELETE FROM groups_obs 
            WHERE group_id = :group_id AND "GO_name" = :obs_name
        """)
        await self.execute(delete_query, {'group_id': group_id, 'obs_name': obs_name})

        return obs_id

    async def remove_user_obs_by_id(self, user_id: str, obs_id: str):
        delete_query = text("""
            DELETE FROM user_obs_info
            WHERE user_id = :user_id AND OBS_id = :obs_id
        """)
        await self.execute(delete_query, {'user_id': user_id, 'obs_id': obs_id})

    async def get_users_obs(self, user_id: str) -> List[List[Any]]:
        query = text("""
            SELECT us."UO_name", ob."OBS_ip", ob."OBS_port"
            FROM users_obs us INNER JOIN obs ob ON us."OBS_id" = ob."OBS_id"
            WHERE us.user_id = :user_id
        """)
        result = await self.execute(query, {'user_id': int(user_id)})
        res = [[row[0], row[1], row[2]] for row in result.fetchall()]
        return res

    async def get_groups_obs(self, group_id: str) -> List[List[Any]]:
        query = text("""
            SELECT "GO_name", OBS."OBS_ip", OBS."OBS_port"
            FROM groups_obs
            JOIN obs ON groups_obs."OBS_id" = obs."OBS_id"
            WHERE group_id = :group_id
        """)
        result = await self.execute(query, {'group_id': group_id})
        return [[row[0], row[1], row[2]] for row in result.fetchall()]


    async def create_planned_stream(self, user_id: str, obs_name: str, start_time: datetime, end_time: datetime) -> bool:
        # Get OBS_id based on user and OBS name
        get_obs_id_query = text("""
            SELECT obs.OBS_id 
            FROM user_obs_info
            JOIN obs ON user_obs_info.OBS_id = obs.OBS_id
            WHERE user_obs_info.user_id = :user_id AND user_obs_info.UO_name = :obs_name
        """)
        obs_id_result = await self.execute(get_obs_id_query, {'user_id': user_id, 'obs_name': obs_name})
        obs_id = await obs_id_result.scalar()

        if not obs_id:
            raise HTTPException(status_code=404, detail='OBS stand not found')

        # Check for interval conflicts
        check_conflict_query = text("""
            SELECT 1 FROM schedule
            WHERE OBS_id = :obs_id AND NOT (
                (S_start >= :end_time) OR 
                (S_end <= :start_time)
            )
        """)
        conflict_result = await self.execute(check_conflict_query, {'obs_id': obs_id, 'start_time': start_time, 'end_time': end_time})
        conflict_exists = await conflict_result.scalar()

        if conflict_exists:
            return False

        # Add new interval
        insert_query = text("""
            INSERT INTO schedule (OBS_id, S_start, S_end) 
            VALUES (:obs_id, :start_time, :end_time)
        """)
        await self.execute(insert_query, {'obs_id': obs_id, 'start_time': start_time, 'end_time': end_time})

        return True

    async def flush_old_intervals(self, obs_ip: str) -> None:
        # Get OBS ID from OBS IP
        get_obs_id_query = text("""
            SELECT OBS_id FROM obs
            WHERE OBS_ip = :obs_ip
        """)
        obs_id_result = await self.execute(get_obs_id_query, {'obs_ip': obs_ip})
        obs_id = await obs_id_result.scalar()

        if not obs_id:
            raise HTTPException(status_code=404, detail='OBS with this IP not found')

        # Delete old intervals
        delete_query = text("""
            DELETE FROM schedule 
            WHERE OBS_id = :obs_id AND S_end < CURRENT_TIMESTAMP
        """)
        await self.execute(delete_query, {'obs_id': obs_id})

    async def get_obs_intervals(self, user_id: str, obs_name: str) -> Tuple[List[Tuple[datetime, datetime]], str]:
        # Get OBS IP and OBS ID based on user ID and OBS name
        get_obs_query = text("""
            SELECT obs.OBS_id, obs.OBS_ip FROM user_obs_info
            JOIN obs ON user_obs_info.OBS_id = obs.OBS_id
            WHERE user_id = :user_id AND UO_name = :obs_name
        """)
        obs_result = await self.execute(get_obs_query, {'user_id': user_id, 'obs_name': obs_name})
        obs_info = await obs_result.fetchone()

        if not obs_info:
            raise HTTPException(status_code=404, detail='OBS with this name not found')

        obs_id, obs_ip = obs_info

        # Get all intervals for this OBS ID
        get_intervals_query = text("""
            SELECT S_start, S_end FROM schedule
            WHERE OBS_id = :obs_id
        """)
        intervals_result = await self.execute(get_intervals_query, {'obs_id': obs_id})
        intervals = [(row['S_start'], row['S_end']) for row in await intervals_result.fetchall()]

        return intervals, obs_ip
