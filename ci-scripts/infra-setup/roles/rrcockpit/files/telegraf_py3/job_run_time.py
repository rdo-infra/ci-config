import re
import requests
from datetime import datetime, time
import sys
import os

def date_diff_in_seconds(dt2, dt1):
  timedelta = dt2 - dt1
  return timedelta.days * 24 * 3600 + timedelta.seconds

def dhms_from_seconds(seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        return (hours, minutes, seconds)

def strip_date_time_from_string(input_string):
    ro = re.compile(r'[\d*-]*\d* [\d*:]*')
    return ro.search(input_string).group()

def convert_string_date_object(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')

def download_file(url):
    r = requests.get(url, stream = True)
    with open("/tmp/job-output.txt","wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)    

def delete_file(path):
    os.remove(path)

def main():
    url = sys.argv[1] + "job-output.txt"
    download_file(url)
    with open("/tmp/job-output.txt", "r") as file:
        first_line = file.readline()
        for last_line in file:
            pass
    start_time = strip_date_time_from_string(first_line)
    start_time_ob = convert_string_date_object(start_time)
    print(f"Start time is {start_time_ob}")
    end_time = strip_date_time_from_string(last_line)
    end_time_ob = convert_string_date_object(end_time)
    print(f"End time is {end_time_ob}")

    hours, minutes, seconds = dhms_from_seconds(date_diff_in_seconds(end_time_ob, start_time_ob))
    print(f"Took {hours} hr {minutes} mins {seconds} secs")
    delete_file("/tmp/job-output.txt")

if __name__ == "__main__":
    main()
