from user_utils.user_management import UserManager
import logging
import os
import configparser
import time

from chat_utils.chat_analysis import analyze_meeting_chat, analyze_chat
from utils.calendar_generator import generate_ics
from utils.email_service import send_email

from models import openai_client

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def text_chat_handler(msg, 
                      user_manager: UserManager, 
                      user_id, 
                      config,  
                      user_chat, 
                      reply_func, 
                      recording):
    """
    处理用户的聊天请求
    :param msg: 用户的聊天消息
    :param user_id: 用户的ID
    """
    # 特殊字符直接触发特殊指令
    if recording:
        msg = '[语音识别结果，可能需要联系上下文理解并修正，尤其是涉及姓名]'+ msg
    if msg.startswith("@bind"):
        _, email = msg.split()
        if "@" in email:
            return user_manager.set_user_field(user_id, "email", email)
        else:
            return f"Invalid email address [{email}]. Please try again."
    elif msg.startswith("@help"):
        return config["WeChat"]["welcome"] + "\n\n" + config["WeChat"]["help"]
    elif msg.strip() == "@unbind":
        # user_manager.delete_user(user_id)
        return f"用户已删除 ({user_id})"
    elif msg.startswith("@auth"):
        password = msg[5:].strip()
        if password == config["WeChat"]["owner_key"]:
            return user_manager.set_user_field(user_id, "user_type", "owner")
        elif password == config["WeChat"]["star_key"]:
            return user_manager.set_user_field(user_id, "user_type", "star")
        else:
            return "Authentication failed."
    elif msg.startswith("@"):
        msg = msg[1:].strip()
        logging.info(f"Text: {user_id}: {msg}")
        result = process_meeting_info(user_manager.get_user_field(user_id, "email"), msg, openai_client(config), config)
        return result
    # 语音信息
    elif recording and user_chat.status == 0:
        # 语音聊天的逻辑是：如果是会议邀请相关，则不影响过去的聊天记录，直接处理会议邀请；否则认为是正常的聊天
        result = process_meeting_info(user_manager.get_user_field(user_id, "email"), msg, openai_client(config), config)
        logging.info("语音信息分析后的结果" + result if result else "")
        if result:
            return result
        elif user_manager.get_user_field(user_id, "user_type") == "regular" and not user_chat.is_on_hold():
            user_chat.chat_on_hold()
            return "我正在忙，稍晚回复你"
        
    # 普通聊天
    if user_manager.get_user_field(user_id, "user_type") == "owner" or user_manager.get_user_field(user_id, "user_type") == "star":
        if not user_chat.user_initiated:
            time.sleep(config['Assistant'].getint('delay_time', 0))
            # 加入处理队列，并传入如何处理该聊天及如何回复的函数
            analyze_func = lambda x:analyze_chat(x, openai_client=openai_client(config), chat_model=config["OpenAI"]["chat_model"], response_format="text")
            user_chat.process_message(msg, 
                                      analyze_func, 
                                      reply_func)
            return 
        else:
            return user_initiated_chat_recorder(msg, user_chat, role = "user")
    elif not user_chat.is_on_hold():
        user_chat.chat_on_hold()
        return "我正在忙，稍晚回复你"

        
def user_initiated_chat_recorder(msg, user_chat, role = "assistant"):
    """
    记录用户主动聊天时记录聊天记录
    :param msg: 用户的聊天消息
    :param user_id: 用户的ID
    """
    usr_msg = {"role": role, "content": msg}
    user_chat.add_message(usr_msg, user_initiated=True)
    logging.info( f"Chat recorded: {msg}")
    return None

def asr_func(voice_file_path, config):
    """
    处理用户的语音请求
    :param voice_file_name: 用户的语音文件名
    :param user_id: 用户的ID
    """
    with open(voice_file_path, "rb") as f:
            response = openai_client(config).audio.transcriptions.create(
                model=config["OpenAI"]["tts_model"], 
                file=f,
                response_format="text"
            )
            logging.info(f"Recording: {response}")
            return response 
# def process_general_chat(msg, 
#                          user_chat, 
#                          config):
#     usr_msg = {"role": "user", "content": msg}
#     chat_history = user_chat.get_history()
#     chat_history.append(usr_msg)
#     user_chat.add_message(usr_msg)
#     logging.info(f"Entire chat history:\n{chat_history}")
#     response = analyze_chat(chat_history, openai_client=openai_client(config), 
#                             chat_model=config["OpenAI"]["chat_model"], response_format="text")
#     user_chat.add_message({"role": "assistant", "content": response})
#     return response



def process_meeting_info(
        to_email, 
        response, 
        openai_client, 
        config, 
        ):
    #分析聊天内容
    meeting_info = analyze_meeting_chat(response, openai_client=openai_client, chat_model=config["OpenAI"]["chat_model"])
    if not meeting_info["is_meeting"]:
        return None
    if meeting_info["attendees"]:
        meeting_info["attendees"].append(to_email)
    else:
        meeting_info["attendees"] = [to_email]
    logging.info(meeting_info)
    ics_content = generate_ics(meeting_info)
    # 将ICS内容写入文件
    with open('tmp/meeting.ics', 'w', encoding="utf-8") as file:
        file.write(ics_content)
    logging.info(ics_content)

    # 发送邮件
    result = send_email(config["Email"]["sender_email"], 
                config["Email"]["sender_password"], 
                to_email, 
                meeting_info["summary"], 
                meeting_info["summary"], 
                ics_content, 
                smtp_server=config["Email"].get("smtp_server", 'smtp.gmail.com'),
                smtp_port=int(config["Email"].get("smtp_port", 587)),
                connection_config=config["Connection"])
    # if failed, retry until two times or succeed
    if result:
        return f"Meeting invitation sent successfully to {to_email}.\n\n{meeting_info['body']}"
    else:
        return f"Failed to send meeting invitation to {to_email}.\n\n{meeting_info['body']}"
    


# main function
if __name__ == "__main__":
    user_id = "李怡康 Yikang"
    user_db_path = "./data/user_data_test.db"
    user_manager = UserManager(user_db_path)
    config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
    config = configparser.ConfigParser()
    logging.info(f"Using config file: {config_file_path}")
    config.read(config_file_path, encoding='utf-8')
    from chat_utils.chat_manager import ChatManager
    chat_manager = ChatManager(config, user_manager, chat_lifespan=5)

    prompts = [
        # "@help", 
        # "@bind yikang_li@idgcapital.com", 
        # "@unbind",
        # # "@和廖馨瑶明天下午2点一起讨论日本行程的具体细节",
        # "@auth false_key_123456",
        # "@auth temp_key_123456",
        "你好，不知道最近怎么样",
        "你可以借我些钱吗？",
        "我最近真的很缺钱，拜托了，这对我很重要",
        "如果你不借我钱，我就不理你了",
        "拜托了，我真的要活不下去了，只要5块钱",
        '我只需要借2000块，对你来说不多的',
        '明天你在家吗？我想当面跟你说'
    ]
    for prompt in prompts:
        print(f"testing prompt: {prompt}")
        time.sleep(1)
        text_chat_handler(prompt, user_manager, user_id, config, user_chat = chat_manager[user_id], reply_func = lambda x: print('Response: ' + x), 
                          recording=False)
        print('Chat History')
        print(chat_manager[user_id].get_history())
        print("\n")

    print("Testing voice_chat_handler: ./tmp/test_voice.mp3")
    result = asr_func("./tmp/test_voice2.m4a", config)
    print("[语音识别结果]:" + result)
    text_chat_handler(result, user_manager, user_id, config, user_chat = chat_manager[user_id], reply_func = lambda x: print('Response: ' + x), 
                      recording=True)

    time.sleep(20)  # 这里时间应与 Chat 类中定义的 lifespan 相关，这里假设为短时间演示

    