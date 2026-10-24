from datetime import datetime

def calDiffMinute(date1:datetime, date2:datetime):
    return (date1-date2).total_seconds() / 60