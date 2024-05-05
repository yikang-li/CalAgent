import configparser
from openai import OpenAI
import json
from datetime import datetime, timedelta
import pytz
import httpx
import os
import logging


config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
config = configparser.ConfigParser()
config.read(config_file_path, encoding='utf-8')

def analyze_chat(chat_content, 
                 openai_client=None, 
                 chat_model="gpt-3.5-turbo-1106", 
                 response_format="text"):
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
        messages=chat_content,
        timeout=60,
        response_format= {"type":response_format}
    )

    text = completion.choices[0].message.content
    return text

def analyze_meeting_chat(chat_content, openai_client=None, chat_model="gpt-3.5-turbo-1106"):
    """
    调用ChatGPT API分析聊天记录，并提取关键信息
    :param chat_content: 聊天内容的字符串
    :return: 一个包含提取出的关键信息的字典
    """
    def generate_meeting_assistant_prompt(chat_content):
        """
        根据聊天内容生成适合ChatGPT的提示语
        :param chat_content: 原始的聊天内容字符串
        :return: 生成的提示语
        """
        now = datetime.now()
        date_time_str = now.strftime("%Y-%m-%d %H:%M:%S") + " " + now.strftime("%A")

        return f"你作为日程创建助理，根据提供的聊天记录提取会议的关键信息用于日程创建，请注意当前收到信息的时间是 {date_time_str}, 以JSON格式输出会议信息，请不要脑补聊天记录中没有的信息。\n\n" + """期望的输出格式如下：{
            "summary": （根据聊天内容提取日程/提醒的主题，需要包含【参与对象】、【做什么事】等，例如“和XXX一起做XXX”或者“XX小组讨论会”等， 如果不涉及则返回空）,
            "start_time": （提取开始时间，格式为YYYY-MM-DD HH:MM; 如果时间没有具体到小时和分钟，则假定为当天的9:00; 如果收到信息的时间是凌晨0点到4点之间，且聊天中使用例如"明天/后天"这样的相对日期，则默认将时间提前一天）,
            "duration": （持续时长，单位为分钟，如果没有说明时间，则根据类别选择，会议默认为60分钟、吃饭等娱乐活动默认2小时、提醒则默认为15分钟）,
            "attendees": （参会者，所有提到的名字、邮箱都被列为参会者，不用包含自己）,
            "location": （参会地址或者所用会议工具，如Zoom（包含会议号或链接）、腾讯会议（包含会议号或链接）、微信语音、电话号码（包含电话号码）等，如果未提及，则输出'待定'）,
            "is_meeting": （根据聊天判断是否可以需要预定日程或者设置提醒，满足其一则返回True，否则返回False),
            }\n
            """ + f"聊天记录为: \n{chat_content}\n请输出："
    
    chat_content = [{"role": "user", "content": generate_meeting_assistant_prompt(chat_content)}]
    text = analyze_chat(chat_content, 
                        openai_client=openai_client, 
                        chat_model=chat_model, 
                        response_format="json_object")
    def parse_info(text):
        """
        解析ChatGPT返回的文本，提取关键信息
        :param text: ChatGPT返回的文本
        :return: 一个包含提取出的关键信息的字典
        """
        info = json.loads(text)
        info["start_time"] = datetime.strptime(info["start_time"], "%Y-%m-%d %H:%M")
        # # 如果是凌晨4点之前，则在开始时间上提前一天
        # if datetime.now().hour < 4:
        #     info["start_time"] = info["start_time"] - timedelta(days=1)
        # 如果开始时间晚于当前时间，则选择当前时间后1一小时的整点开始
        if info["start_time"] < datetime.now():
            info["start_time"] = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        ## 指定为国内时区（未来增加时区感知）
        ## 标准做法是"Asia/Shanghai"，如果使用"UTC+8"，则在识别上会有问题（也有夏令时的问题）
        tz_utc_8 = pytz.timezone('Asia/Shanghai')
        info["start_time"] = info["start_time"].replace(tzinfo=tz_utc_8)
        info["duration"] = timedelta(minutes=info["duration"])
        info["body"] = text
        return info

    # 解析text以提取需要的信息
    info = parse_info(text)
    return info

def analyze_conversation(conversation_history: list, 
                         user_tags: list,
                         openai_client=None, 
                         chat_model="gpt-3.5-turbo-1106") -> dict:
    """
    分析本轮聊天历史记录，分析是否有关于聊天对象的重要记忆或对于聊天对象的新的认知（标签）
    :param conversation_history: list 聊天历史记录
    :param user_tags: list 用户标签
    :return: 一个包含提取出的关键信息的字典
    """
    now = datetime.now()
    date_time_str = now.strftime("%Y-%m-%d %H:%M:%S") + " " + now.strftime("%A")
    conversation_history = "\n".join([f"{item['role']}: {item['content']}" for item in conversation_history if item['role'] != "system"])
    user_tags = ", ".join(user_tags)
    logging.debug(f"Conversation history: \n{conversation_history}")
    prompt = f"当前时间为：{date_time_str} 请根据提供的聊天记录，从聊天中提取跟聊天对象(user)的重要信息，请不要补充聊天记录中没有提及的信息，但可以根据聊天记录推测user的标签。你的身份是assistant。\n\n" \
        + """请以Json格式输出如下信息：{
        "memory": （用简要的语言总结从聊天记录中提取的重要记忆，重要记忆是指跟对聊天对象(user)能有更深了解的聊天细节，例如他的喜好或者他对我的好/不好等，如果没有或者已提供的用户记忆已经涵盖了该内容则返回空）,
        "tags": （对于聊天对象的新的标签，通常是指有助于快速了解某个人身份、背景、特点等信息，例如“AI领域投资人”、“AI技术研发”等，如果没有或者已提供的用户标签已经涵盖了该内容则返回空）,
        }\n
        """ + f"本轮的聊天记录为: \n[[{conversation_history}]]\n"
    if user_tags and len(user_tags) > 0:
        prompt += f"已有的用户标签为：[[{user_tags}]]\n请输出：" 
    else:
        prompt += "请输出："
    logging.debug(f"Conversation history: \n{prompt}")
    chat_content = [{"role": "user", "content": prompt}]
    conversation_summary = analyze_chat(chat_content, 
                        openai_client=openai_client, 
                        chat_model=chat_model, 
                        response_format="json_object")
    return json.loads(conversation_summary)


# 示例使用
if __name__ == "__main__":
    # chat_content = "我和廖馨瑶明天下午2点一起讨论日本行程的具体细节。"
    # info = analyze_meeting_chat(chat_content)
    # print(info)
    # set logging level
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    chat_history = [
        {'role': 'system', 'content': '你是李怡康（使用者）的AI分身，帮助使用者处理跟重要朋友的对话，你是设计用来专门跟某个特定聊天对象交流，因此需要根据历史聊天记录、聊天对象的信息来生成个性化的回复，做到礼貌、优雅、幽默，如果遇到无法回答的问题，则礼貌地进行回避。\n以下是使用者为该聊天对象标注的标签：'}, 
         {'role': 'user', 'content': '你好，不知道最近怎么样'}, 
         {'role': 'assistant', 'content': '你好，最近还不错，谢谢关心。你最近过得如何呢？有什么新鲜事儿吗？'}, 
         {'role': 'user', 'content': '你可以借我些钱吗？'},
         {'role': 'assistant', 'content': '抱歉，我作为一个AI分身是无法提供金钱支持的。不过，如果有什么其他方面我可以帮忙的，尽管开口。'},
        ]
    user_tags = ["AI领域投资人", "AI技术研发", "商汤科技", "MSRA", "IDG资本", "Facebook Reality Labs"]
    conversation_summary = analyze_conversation(chat_history, user_tags)
    print(conversation_summary)
    