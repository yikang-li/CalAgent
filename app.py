import itchat
from itchat.content import *
from itchat import accept_friend
import configparser
import argparse
import logging
import os
from chat_utils.chat_handler import text_chat_handler, voice_chat_handler, user_initiated_chat_recorder
from chat_utils.chat_manager import ChatManager
from user_utils.user_management import UserManager

# set logging level
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
config = configparser.ConfigParser()
chat_manager = None
user_manager = None

def get_id(user_name):
    """
    Get user_id from user_name
    :param user_name: user_name
    :return: user_id
    """
    if user_name is None:
        friend = itchat.search_friends(name=user_name)
    else:
        friend = itchat.search_friends(name=user_name)[0]  # 获取第一个搜索结果
    return friend['UserName']

def send_message(user_id, message):
    """
    Send message to user
    :param user_id: user_id
    :param message: message to send
    :return: None
    """
    to_user_id = get_id(user_id)
    itchat.send_msg(message, toUserName=to_user_id)


def configuration():
    parser = argparse.ArgumentParser(description='WeChat Meeting Assistant')
    default_config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
    parser.add_argument('--config', default=default_config_file_path, help='path to the config file')
    args = parser.parse_args()
    config_file_path = args.config
    logging.info(f"Using config file: {config_file_path}")
    global config
    config.read(config_file_path, encoding='utf-8')

    global chat_manager
    global user_manager
    user_manager = UserManager(config['UserManagement']['user_db_path'], 
                               owner_id=config['UserManagement']['owner'])
    chat_manager = ChatManager(config, user_manager, 
                               chat_lifespan=int(config['Assistant']['chat_lifespan']), 
                               chat_callback=lambda x: send_message(config['UserManagement']['owner'], x))

@itchat.msg_register([TEXT])
def text_reply(msg):
    logging.info(f"Text: {msg.user.NickName}: {msg.text}")
    if msg['FromUserName'] == get_id(None) and (user_manager.get_user_field(msg.user.NickName, "user_type") == "owner" or user_manager.get_user_field(msg.user.NickName, "user_type") == "star"):
        # 如果手动发出的信息，不用进行处理，仅仅用于记录
        # 该功能仅对标星用户有效
        logging.info(f"主动发送信息给 [{msg.user.NickName}]: {msg.text}")
        user_initiated_chat_recorder(msg.text, chat_manager[msg.user.NickName])
        return
    return text_chat_handler(msg.text, user_manager, msg.user.NickName, config, 
                             user_chat = chat_manager[msg.user.NickName])


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
        result = voice_chat_handler(file_path, user_manager, msg.user.NickName, config)
        os.remove(file_path)
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
    configuration()
    # 登录
    itchat.auto_login(hotReload=False, enableCmdQR=2, picDir='./tmp/QRCode.png')
    itchat.run(True)

    # 默认通过环境变量来配置config.ini文件路径， 默认采用./config.ini
    # export PA_CONFIG_PATH=./config_server.ini
