import datetime
import pytz

def get_now():
    return datetime.datetime.now(pytz.timezone('Europe/Moscow'))