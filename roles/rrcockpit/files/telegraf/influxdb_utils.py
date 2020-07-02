import time
from datetime import datetime


def format_ts_from_float(ts):
    return int(ts) * 1000000000


def format_ts_from_date(ts):
    return format_ts_from_float(time.mktime(ts.timetuple()))


def format_ts_from_str(ts, pattern='%Y-%m-%d %H:%M:%S'):
    return format_ts_from_date(datetime.strptime(ts, pattern))
