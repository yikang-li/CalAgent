import smtplib
from contextlib import contextmanager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import socks
import socket
import os
import configparser
from chat_analysis import analyze_chat
import logging

@contextmanager
def use_proxy(proxy_type, proxy_addr, proxy_port, proxy_username=None, proxy_password=None):
    # import pdb
    # pdb.set_trace()
    if proxy_addr is None or proxy_port is None:
        yield
        return
    logging.info(f'Using SOCKS proxy: {proxy_addr}:{proxy_port}')
    original_socket = socket.socket
    try:
        socks.setdefaultproxy(proxy_type, proxy_addr, proxy_port, username=proxy_username, password=proxy_password)
        socks.wrapmodule(smtplib)
        yield
    finally:
        socket.socket = original_socket


def send_email(sender_email, 
                sender_password, 
                recipient_email, 
                subject, 
                body, 
                ics_content, 
                smtp_server='smtp.gmail.com',
                smtp_port=587, 
                proxy=(None, None)):
    """
    使用SMTP协议发送电子邮件，包含一个.ics日历文件作为附件。

    :param sender_email: 发件人的电子邮件地址
    :param sender_password: 发件人的电子邮件密码或授权码
    :param recipient_email: 收件人的电子邮件地址
    :param subject: 邮件主题
    :param body: 邮件正文
    :param ics_content: iCalendar (.ics) 文件的内容
    """
    # 创建MIMEMultipart对象
    msg = MIMEMultipart('mixed')
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # 添加邮件正文
    msg.attach(MIMEText(body, 'plain'))

    # 添加直接可识别的日历事件
    part_calendar = MIMEText(ics_content,'calendar; method=REQUEST')
    msg.attach(part_calendar)

    # 设置.ics文件作为附件
    part_attachment = MIMEBase('text', 'calendar', name="event.ics")
    part_attachment.set_payload(ics_content.encode('utf-8'))
    encoders.encode_base64(part_attachment)
    part_attachment.add_header('Content-Disposition', 'attachment', filename="event.ics")
    msg.attach(part_attachment)


    # 使用SMTP服务器发送邮件
    # 设置 socks 代理
    try:
        # 设置 socks 代理
        with use_proxy(socks.PROXY_TYPE_SOCKS5, *proxy):
            # import pdb
            # pdb.set_trace()
            logging.info(f'Connecting SMTP: {smtp_server}:{smtp_port}')
            server = smtplib.SMTP(smtp_server, smtp_port)  # 替换为你的SMTP服务器地址和端口
            # server.set_debuglevel(1)
            server.starttls()  # 启用TLS加密
            logging.info(f'Login SMTP: {sender_email}')
            server.login(sender_email, sender_password)
            text = msg.as_string()
            logging.info(f'Sending email...')
            server.sendmail(sender_email, recipient_email, text)
            server.quit()
            logging.info("Successfully sending email.")
        return True
    except Exception as e:
        print(f"Failed to send email：{e}")
        return False

# 示例使用
if __name__ == "__main__":
    # load config for test
    config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
    config = configparser.ConfigParser()
    config.read(config_file_path, encoding='utf-8')

    sender_email = config["Email"]["sender_email"]
    sender_password = config['Email']["sender_password"]
    # Gmail proxy settings
    if config["Connection"].get("socks_port", None):
        socks_proxy = [config["Connection"]["proxy"], 
                    int(config["Connection"]["socks_port"]), 
                    config["Connection"].get("proxy_username", None), 
                    config["Connection"].get("proxy_password", None)]
    else:
        socks_proxy = (None, None)
    recipient_email = "yikang_li@idgcapital.com"
    subject = "和廖馨瑶讨论项目"
    body = "和廖馨瑶讨论项目"
    with open('data/meeting.ics', 'r', encoding="utf-8") as file:
        ics_content = file.read()
        print(ics_content)
    # ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\n..."  # 这里应是生成的ICS内容
    send_email(sender_email, sender_password, recipient_email, subject, body, ics_content, proxy = socks_proxy)