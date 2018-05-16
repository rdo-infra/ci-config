import time
from datetime import datetime

def format_ts_from_date(ts):
    return int(
        time.mktime(ts.timetuple())) * 1000000000

def format_ts_from_str(ts, pattern='%Y-%m-%d %H:%M:%S'):
    return format_ts_from_date(datetime.strptime(ts, pattern))
