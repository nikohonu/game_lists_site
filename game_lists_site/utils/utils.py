import datetime as dt


def delta_gt(datetime, days=1):
    current_date = dt.datetime.now()
    return (current_date - datetime).days >= days
