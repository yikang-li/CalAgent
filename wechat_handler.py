import user_management
import logging
import os
import configparser


from chat_analysis import analyze_chat
from calendar_generator import generate_ics
from email_service import send_email


def bind_email(wechat_id, email):
    """
    处理用户绑定邮箱的逻辑
    :param wechat_id: 用户的微信ID
    :param email: 用户想要绑定的邮箱地址
    """
    # 这里调用user_management.py的功能
    with user_management.create_connection(user_management.DATABASE) as conn:
    # conn = user_management.create_connection(user_management.DATABASE)
        if user_management.get_user_email(conn, wechat_id) is None:
            user_management.add_user(conn, wechat_id, email)
            return f"Email {email} bound to {wechat_id} successfully."
        else:
            user_management.update_user_email(conn, wechat_id, email)
            return f"Email for {wechat_id} updated to {email}."
    # conn.close()

def get_email(wechat_id):
    """
    处理用户获取邮箱的逻辑
    :param wechat_id: 用户的微信ID
    """
    # 这里调用user_management.py的功能
    with user_management.create_connection(user_management.DATABASE) as conn:
    # conn = user_management.create_connection(user_management.DATABASE)
        email = user_management.get_user_email(conn, wechat_id)
    # conn.close()
    if email is None:
        return False
    else:
        return email


def unbind_email(wechat_id):
    """
    处理用户绑定邮箱的逻辑
    :param wechat_id: 用户的微信ID
    :param email: 用户想要绑定的邮箱地址
    """
    # 这里调用user_management.py的功能
    with user_management.create_connection(user_management.DATABASE) as conn:
    # conn = user_management.create_connection(user_management.DATABASE)
        if user_management.get_user_email(conn, wechat_id) is None:
            return f"No such user: {wechat_id}"
        else:
            email = user_management.get_user_email(conn, wechat_id)
            user_management.delete_user(conn, wechat_id)
            return f"Unbind {email} for {wechat_id}."

def process_meeting_info(
        wechat_id, 
        response, 
        openai_client, 
        config, 
        ):
    # 验证是否绑定邮箱
    to_email = get_email(wechat_id)
    if not to_email:
        return "Please bind your email address first. '@help' for help."
    
    #分析聊天内容
    meeting_info = analyze_chat(response, openai_client=openai_client, chat_model=config["OpenAI"]["chat_model"])
    if not meeting_info["is_meeting"]:
        return "No meeting information found in the message."
    if meeting_info["attendees"]:
        meeting_info["attendees"].append(to_email)
    else:
        meeting_info["attendees"] = [to_email]
    logging.info(meeting_info)
    ics_content = generate_ics(meeting_info)

    # Gmail proxy settings
    if config["Connection"].get("socks_port", None):
        socks_proxy = [config["Connection"]["proxy"], 
                    int(config["Connection"]["socks_port"]), 
                    config["Connection"].get("proxy_username", None), 
                    config["Connection"].get("proxy_password", None)]
        logging.info(f"Using proxy: {socks_proxy}")
    else:
        socks_proxy = None

    # 发送邮件
    result = send_email(config["Email"]["sender_email"], 
                config["Email"]["sender_password"], 
                to_email, 
                meeting_info["summary"], 
                meeting_info["summary"], 
                ics_content, 
                smtp_server=config["Email"].get("smtp_server", 'smtp.gmail.com'),
                smtp_port=int(config["Email"].get("smtp_port", 587)),
                proxy=socks_proxy)
    # if failed, retry until two times or succeed
    if result:
        return f"Meeting invitation sent successfully to {to_email}.\n\n{meeting_info['body']}"
    else:
        return f"Failed to send meeting invitation to {to_email}.\n\n{meeting_info['body']}"
    


# main function
if __name__ == "__main__":
    wechat_id = "李怡康 Yikang"
    config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
    config = configparser.ConfigParser()
    logging.info(f"Using config file: {config_file_path}")
    config.read(config_file_path, encoding='utf-8')

    print(f"Bind Email: {bind_email(wechat_id, 'yikang_li@idgcapital.com')}")
    print(f"Get Email: {get_email(wechat_id)}")
    response = "我和廖馨瑶明天下午2点一起讨论日本行程的具体细节。"
    print(f"Process meeting info ({response}):\n")
    print(process_meeting_info(wechat_id, response, None, config))