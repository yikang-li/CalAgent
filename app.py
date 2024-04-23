import itchat
from itchat.content import *
from itchat import accept_friend
import configparser
import logging
import os
import httpx
from wechat_handler import *


from chat_analysis import analyze_chat
from calendar_generator import generate_ics
from email_service import send_email

from openai import OpenAI

# set logging level
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
config = configparser.ConfigParser()
logging.info(f"Using config file: {config_file_path}")
config.read(config_file_path, encoding='utf-8')


# OpenAI proxy settings
if config["Connection"].get("http_port", None):
    if config["Connection"].get("proxy_username", None):
        http_proxy = f"http://{config['Connection']['proxy_username']}:{config['Connection']['proxy_password']}@{config['Connection']['proxy']}:{config['Connection']['http_port']}"
    else:
        http_proxy = f"http://{config['Connection']['proxy']}:{config['Connection']['http_port']}"
    httpx_client = httpx.Client(proxies={"http://": http_proxy, "https://": http_proxy})
    logging.info(f"Using proxy: {http_proxy}")
else:
    httpx_client = None
openai_client = OpenAI(api_key=config["OpenAI"]["api_key"], http_client=httpx_client)


@itchat.msg_register([TEXT])
def text_reply(msg):
    logging.info(f"Text: {msg.user.NickName}: {msg.text}")
    if msg.text.startswith("@bind"):
        _, email = msg.text.split()
        if "@" in email:
            return bind_email(msg.user.NickName, email)
        else:
            return f"Invalid email address [{email}]. Please try again."
    elif msg.text.startswith("@help"):
        return config["WeChat"]["welcome"] + "\n\n" + config["WeChat"]["help"]
    elif msg.text.startswith("@unbind"):
        unbind_email(msg.user.NickName)
        return "Received: " + msg.text
    elif msg.text.startswith("@"):
        response = msg.text[1:].strip()
        logging.info(f"Text: {msg.user.NickName}: {response}")
        result = process_meeting_info(msg.user.NickName, response, openai_client, config)
        return result
    # else:
    #     msg.user.send(f"Cannot recognize the command: {msg.text}. Please type @help for help.")
    # return "Received but ignored: " + msg.text

# @itchat.msg_register([PICTURE, RECORDING, ATTACHMENT, VIDEO])
@itchat.msg_register([RECORDING])
def download_files(msg):
    logging.info(f"File: {msg.user.NickName}: {msg.fileName}")

    file_path = os.path.join('tmp', msg.fileName)
    msg.download(file_path)
    # 判断消息类型
    typeSymbol = {
        PICTURE: 'img',
        VIDEO: 'vid',
    }.get(msg.type, 'fil')

    # 如果是语音消息，进行ASR处理
    if msg.type == RECORDING:
        with open(file_path, "rb") as f:
            response = openai_client.audio.transcriptions.create(
                model=config["OpenAI"]["tts_model"], 
                file=f,
                response_format="text"
            )
        os.remove(file_path)
        # 打印转录结果
        logging.info(f"Recording: {msg.user.NickName}: {response}")
        result = process_meeting_info(msg.user.NickName, response, openai_client, config)
        return result
        
    else:
        # 对于非语音消息，返回原处理方式
        return '@%s@%s' % (typeSymbol, msg.fileName)
    

@itchat.msg_register(FRIENDS)
def add_friend(msg):
    logging.info("New friend request received.")
    accept_friend(msg.user["UserName"], msg['RecommendInfo']['Ticket'])
    msg.user.send(config["WeChat"]["welcome"] + "\n输入@help寻求更多帮助")


# main function
if __name__ == "__main__":
    # 默认通过环境变量来配置config.ini文件路径， 默认采用./config.ini
    # export PA_CONFIG_PATH=./config_server.ini

    # 登录
    itchat.auto_login(hotReload=False, enableCmdQR=2)
    itchat.run(True)