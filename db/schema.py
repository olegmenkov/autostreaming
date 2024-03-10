from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# OBS Table
class OBS(Base):
    __tablename__ = 'obs'

    OBS_id = Column(String(36), primary_key=True)
    OBS_ip = Column(String(40), nullable=False)
    OBS_port = Column(Integer, nullable=False)
    OBS_pswd = Column(String(40), nullable=False)

# Users Table
class Users(Base):
    __tablename__ = 'users'

    U_id = Column(String(36), primary_key=True, unique=True)

# Groups Table
class Groups(Base):
    __tablename__ = 'groups'

    G_id = Column(String(36), primary_key=True)

# Users_OBS Table
class Users_OBS(Base):
    __tablename__ = 'users_obs'

    user_id = Column(Integer, primary_key=True)
    OBS_id = Column(String(36), primary_key=True)
    UO_name = Column(String(40), nullable=False)
    UO_access_grant = Column(Boolean, nullable=False)

# Group_membership Table
class Group_membership(Base):
    __tablename__ = 'group_membership'

    group_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    M_admin = Column(Boolean, nullable=False)

# Groups_OBS Table
class Groups_OBS(Base):
    __tablename__ = 'groups_obs'

    group_id = Column(Integer, primary_key=True)
    OBS_id = Column(String(36), primary_key=True)
    GO_name = Column(String(40), nullable=False)

# Schedule Table
class Schedule(Base):
    __tablename__ = 'schedule'

    OBS_id = Column(String(36), primary_key=True)
    group_id = Column(Integer, primary_key=True)
    S_start = Column(Date, nullable=False)
    S_end = Column(Date, nullable=False)
