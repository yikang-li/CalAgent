from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz

def generate_ics(event_info):
    """
    根据提供的事件信息生成iCalendar (.ics) 文件。

    :param event_info: 一个包含事件信息的字典，应包括：
                       'summary' - 事件的标题或简介
                       'start_time' - 事件开始时间，datetime对象
                       'duration' - 事件持续时间，timedelta对象
                       'attendees' - 参与者的电子邮件列表（可选）
                       'location' - 会议工具或地点 (可选)
    :return: 生成的iCalendar (.ics) 文件内容
    """
    cal = Calendar()
    cal.add('prodid', '-//YK Bot//YK Botverse//EN')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')

    event = Event()
    event.add('summary', event_info['summary'])
    event.add('dtstart', event_info['start_time'])
    event.add('dtend', event_info['start_time'] + event_info['duration'])
    event.add('uid', f"{event_info['start_time'].strftime('%Y%m%dT%H%M%S')}@ykbot.com")
    if event_info.get('location', ""):
        event.add('location', event_info['location'])
    else:
        event.add('location', 'Pending')

    if 'attendees' in event_info and event_info['attendees']:
        for attendee in event_info['attendees']:
            if "@" in attendee:
                event.add('attendee', f"mailto:{attendee}")

    cal.add_component(event)

    # 返回ICS文件的内容
    return cal.to_ical().decode('utf-8')

# 示例使用
if __name__ == "__main__":
    tz_utc_8 = pytz.timezone('Asia/Shanghai')
    event_info = {
        'summary': '项目进度讨论会',
        'start_time': (datetime.now() + timedelta(days=1)).replace(tzinfo=tz_utc_8),
        'duration': timedelta(minutes=60),
        'attendees': ['yikang_li@idgcapital.com', '廖馨瑶'],
        'location': 'Zoom Meeting'
    }
    ics_content = generate_ics(event_info)
    print(ics_content)

    # 将ICS内容写入文件
    with open('data/meeting.ics', 'w', encoding="utf-8") as file:
        file.write(ics_content)
