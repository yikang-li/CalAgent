import configparser
from openai import OpenAI
import json
from datetime import datetime, timedelta, timezone
import httpx
import os


config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
config = configparser.ConfigParser()
config.read(config_file_path, encoding='utf-8')

def analyze_chat(chat_content, openai_client=None, chat_model="gpt-3.5-turbo-1106"):
    """
    调用ChatGPT API分析聊天记录，并提取关键信息
    :param chat_content: 聊天内容的字符串
    :return: 一个包含提取出的关键信息的字典
    """
    if not openai_client:
        if config["Connection"].get("http_port", None):
            if config["Connection"].get("proxy_username", None):
                http_proxy = f"http://{config['Connection']['proxy_username']}:{config['Connection']['proxy_password']}@{config['Connection']['proxy']}:{config['Connection']['http_port']}"
            else:
                http_proxy = f"http://{config['Connection']['proxy']}:{config['Connection']['http_port']}"
            httpx_client = httpx.Client(proxies={"http://": http_proxy, "https://": http_proxy})
        else:
            httpx_client = None
        openai_client = OpenAI(api_key=config["OpenAI"]["api_key"], http_client=httpx_client)

    # Check https://platform.openai.com/docs/models/gpt-3-5 for most updated model name
    completion = openai_client.chat.completions.create(
        model=chat_model,
        messages=[{"role": "user", "content": generate_prompt(chat_content)}],
        timeout=60,
        response_format= { "type":"json_object" }
    )

    text = completion.choices[0].message.content
    # 解析text以提取需要的信息
    info = parse_info(text)
    
    return info

def generate_prompt(chat_content):
    """
    根据聊天内容生成适合ChatGPT的提示语
    :param chat_content: 原始的聊天内容字符串
    :return: 生成的提示语
    """
    now = datetime.now()
    date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    return f"请根据以下聊天记录提取会议的关键信息，目前时间是{date_time_str}, 并以JSON格式输出: \n\n{chat_content}\n\n" + """期望的输出格式如下：{
  "summary": （根据聊天内容提取日程主题，需要包含【参与对象】、【做什么事】等，例如“和XXX一起做XXX”）,
  "start_time": （提取开始时间，格式为YYYY-MM-DD HH:MM, 如果时间没有具体到小时和分钟，则假定为当天的9:00）,
  "duration": （持续时长，单位为分钟，如果没有说明时间，则根据类别选择，会议默认为60分钟、吃饭默认2小时、提醒则默认为15分钟）,
  "attendees": （参会者，所有提到的名字都被列为参会者，不用包含自己，请认真甄别）,
  "location": （参会地址或者所用会议工具，如Zoom、腾讯会议、微信语音、电话号码等，如果未提及，则输出''）,
  "is_meeting": (根据信息判断是否可以涉及日程或者提醒，满足其一则回复True，否则False),
}
请输出：
"""

def parse_info(text):
    """
    解析ChatGPT返回的文本，提取关键信息
    :param text: ChatGPT返回的文本
    :return: 一个包含提取出的关键信息的字典
    """
    info = json.loads(text)
    info["start_time"] = datetime.strptime(info["start_time"], "%Y-%m-%d %H:%M")
    # 如果是凌晨4点之前，则在开始时间上提前一天
    if datetime.now().hour < 4:
        info["start_time"] = info["start_time"] - timedelta(days=1)
    # 如果开始时间晚于当前时间，则选择当前时间后1一小时的整点开始
    if info["start_time"] < datetime.now():
        info["start_time"] = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    # 指定为国内时区（未来增加时区感知）
    tz_utc_8 = timezone(timedelta(hours=8))
    info["start_time"] = info["start_time"].replace(tzinfo=tz_utc_8)
    info["duration"] = timedelta(minutes=info["duration"])
    info["body"] = text
    return info

# 示例使用
if __name__ == "__main__":
    chat_content = "我和廖馨瑶明天下午2点一起讨论日本行程的具体细节。"
    info = analyze_chat(chat_content)
    print(info)
    