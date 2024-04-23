from typing import Any, Union, Tuple
from schemas import CalendarRecording, CalendarStopStream, CalendarStartStream
import simpleobsws

DB_CONFIG = {
    "host": 'localhost',
    "port": 5433,
    "user": 'as_user',
    "password": "as_pass",
    "database": 'as_db'}


def check_intersect(first, second):
    if (second[0] <= first[0]) and (first[1] <= second[1]):
        return True
    if (first[0] <= second[0]) and (second[1] <= first[1]):
        return True
    if (second[0] <= first[1]) and (first[1] <= second[1]):
        return True
    if (first[0] <= second[1]) and (second[1] <= first[1]):
        return True
    return False


def intervals_intersection(intervals: list,
                           target: list) -> Tuple[bool, Any]:
    """
    This function checks if new interval intersects with other
    intervals that already stored
    """
    for interval in intervals:
        if check_intersect(interval, target):
            return False, interval
    return True, target


def config_obsclient_calendar(
        calendar_data: Union[CalendarRecording, CalendarStopStream, CalendarStartStream]):
    ip = calendar_data.ip
    port = calendar_data.port
    password = calendar_data.password
    parameters = simpleobsws.IdentificationParameters(
        ignoreNonFatalRequestChecks=False)
    obsclient = simpleobsws.WebSocketClient(
        url='ws://' + ip + ':' + port,
        password=password,
        identification_parameters=parameters)
    return obsclient
