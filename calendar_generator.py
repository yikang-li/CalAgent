from ics import Calendar, Event
from datetime import datetime, timedelta

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
    event = Event()

    event.name = event_info['summary']
    event.begin = event_info['start_time']
    event.duration = event_info['duration']
    if 'location' in event_info:
        event.location = event_info['location']

    if 'attendees' in event_info and event_info['attendees']:
        for attendee in event_info['attendees']:
            if "@" in attendee:
                event.attendees.add(attendee)

    cal.events.add(event)

    # 返回ICS文件的内容
    return cal.serialize()

# 示例使用
if __name__ == "__main__":
    event_info = {
        'summary': '项目进度讨论会',
        'start_time': datetime(2024, 3, 29, 14, 0),
        'duration': timedelta(minutes=60),
        'attendees': ['allen.li.thu@gmail.com', 'yikang_li@idgcapital.com', "廖馨瑶"],
        'location': 'Zoom Meeting'
    }
    ics_content = generate_ics(event_info)
    print(ics_content)

    # 将ICS内容写入文件
    with open('data/meeting.ics', 'w', encoding="utf-8") as file:
        file.write(ics_content)
