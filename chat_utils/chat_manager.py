import time
from datetime import datetime
import threading
import logging
from queue import Queue, Empty
import os
import configparser
from chat_utils.chat_analysis import analyze_conversation
from chat_utils.chat_handler import analyze_chat
from models import openai_client

# 定义 Chat 类来处理单个聊天的逻辑
class Chat:
    def __init__(self, user_id, 
                 max_conv_history:int = 20, 
                 assistant_description = "个人助理",
                 chat_description = None,
                 lifespan:int=1800):
        self.user_id = user_id
        self.lifespan = lifespan
        self.start_time = time.time()
        self.chat_history = []
        self.expired = False  # 添加一个标志来标记聊天是否过期
        self.max_conversation_history = max_conv_history
        self.system_message = {"role": "system", 
                          "content": f"{assistant_description}\n{chat_description}"}
        # Store the message to process
        self.message_queue = Queue()
        self.lock = threading.Lock()
        # Define the status of Chat
        # 0: Specific Function Mode
        # 1: Chat Mode
        self.status = 0
        self.user_initiated = False
        self.on_hold = False

    def is_active(self):
        # 更新聊天的活跃状态
        if (time.time() - self.start_time) >= self.lifespan:
            self.expired = True
        return not self.expired

    def add_message(self, message, user_initiated=False):
        with self.lock:
            if not self.expired:
                self.chat_history.append(message)
                self.start_time = time.time()
                logging.info(f"Message added to {self.user_id}: {message}")
            else:
                logging.info("Attempted to add message to expired chat.")
            if user_initiated:
                self.user_initiated = True
        # when some conversation history added, switch to chat mode
        self.status = 1

    def process_message(self, message, process_handler, reply_func):
        self.message_queue.put([message, process_handler, reply_func])

    def _process_message(self):
        messages = []
        process_handler = None
        reply_func = None
        while True:
            try:
                message, process_handler, reply_func = self.message_queue.get_nowait()
                messages.append(message)
            except Empty:
                break
        if len(messages) > 0:
            messages = {"role": "user", "content": "\n\n".join(messages)}
            self.add_message(messages)
            chat_history = self.get_history()
            logging.info(f"Entire chat history:\n{chat_history}")
            response = process_handler(chat_history)
            self.add_message({"role": "assistant", "content": response})
            logging.info(f"Response generated: {response}")
            reply_func(response)

    def get_history(self):
        with self.lock:
            return [self.system_message,  *self.chat_history[:self.max_conversation_history]]
    
    def chat_on_hold(self):
        self.on_hold = True

    def is_on_hold(self):
        return self.on_hold

# 定义 ChatManager 类来管理所有活跃的聊天
class ChatManager:
    def __init__(self, config, user_manager, chat_lifespan=1800, chat_callback=None):
        self.active_chats = {}
        self.chat_lifespan = chat_lifespan
        self.user_manager = user_manager
        self.description = config["Assistant"]["assistant_description"]
        self.config = config
        self.chat_callback = chat_callback

    def __getitem__(self, user_id):
        return self.get_chat(user_id)
    
    def is_active_chat(self, user_id):
        return user_id in self.active_chats and self.active_chats[user_id].is_active()

    def get_chat(self, user_id):
        # 检索或创建新的 Chat 实例
        if user_id in self.active_chats and self.active_chats[user_id].is_active():
            return self.active_chats[user_id]
        else:
            user_tags = self.user_manager.get_user_field(user_id, "tags")
            if user_tags and len(user_tags) > 0:
                user_tags = "以下是使用者为该聊天对象标注的标签：" + ", ".join(user_tags)
            else:
                user_tags = "对于该聊天对象，暂无用户标签信息"
            logging.info(f"Creating new chat for user: {user_id}")
            chat = Chat(user_id, max_conv_history = 10, 
                 assistant_description = self.description,
                 chat_description = user_tags,
                 lifespan=self.chat_lifespan)
            self.active_chats[user_id] = chat
            # 启动一个线程来管理聊天的生命周期
            threading.Thread(target=self._expire_chat, args=(user_id,)).start()
            return chat

    def _expire_chat(self, user_id):
        # 管理聊天的生命周期
        while self.active_chats[user_id].is_active():
            time.sleep(3)
            # 一段时间进行一次消息处理
            self.active_chats[user_id]._process_message()

        if len(self.active_chats[user_id].get_history()) <= 1:
            del self.active_chats[user_id]
            logging.info(f"Chat expired and deleted for user: {user_id}")
            return
        result = analyze_conversation(self.active_chats[user_id].get_history(), 
                                              self.user_manager.get_user_field(user_id, "tags"),
                                              openai_client=openai_client(self.config), 
                                              chat_model=self.config["OpenAI"]["instruct_model"])
        summary = f"Chat with {user_id} ended."
        memory = result['memory']
        logging.info(f"Memory extracted from chat with {user_id}: {memory}")
        # 结束聊天时，对聊天记录进行总结，并将其存储到用户的记忆/特征中
        if memory and len(memory) > 0:
            existing_memory = self.user_manager.get_user_field(user_id, "memory")
            existing_memory.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}::{memory}")
            self.user_manager.set_user_field(user_id, "memory", existing_memory)
            summary += f"\nNew memory: {memory}"
        tags = result['tags']
        logging.info(f"Tags extracted from chat with {user_id}: {tags}")
        if tags and len(tags) > 0:
            existing_tags = self.user_manager.get_user_field(user_id, "tags")
            existing_tags.append(tags)
            self.user_manager.set_user_field(user_id, "tags", existing_tags)
            summary += f"\nNew Tags: {tags}"
        del self.active_chats[user_id]
        if self.chat_callback:
            self.chat_callback(summary)
        logging.info(f"Chat expired and deleted for user: {user_id}")

def test():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    # 创建 ChatManager 实例
    DATABASE = 'data/user_data_test.db'
    config_file_path = os.getenv('PA_CONFIG_PATH', './config.ini')
    config = configparser.ConfigParser()
    logging.info(f"Using config file: {config_file_path}")
    config.read(config_file_path, encoding='utf-8')
    from user_utils.user_management import UserManager
    user_manager = UserManager(DATABASE)
    chat_manager = ChatManager(config, user_manager, chat_lifespan=5)

    # 模拟用户标识
    user_id = "user123"

    # 获取或创建 Chat 实例
    chat = chat_manager.get_chat(user_id)
    print(f"Chat created for {user_id}")

    # 添加消息到聊天
    chat.add_message({'role': 'system', 'content': '你是李怡康（使用者）的AI分身，帮助使用者处理跟重要朋友的对话，你是设计用来专门跟某个特定聊天对象交流，因此需要根据历史聊天记录、聊天对象的信息来生成个性化的回复，做到礼貌、优雅、幽默，如果遇到无法回答的问题，则礼貌地进行回避。\n以下是使用者为该聊天对象标注的标签：'})
    chat.add_message({'role': 'user', 'content': '你好，不知道最近怎么样'})
    chat.add_message({'role': 'assistant', 'content': '你好，最近还不错，谢谢关心。你最近过得如何呢？有什么新鲜事儿吗？'})
    chat.add_message({'role': 'user', 'content': '你可以借我些钱吗？'})
    chat.add_message({'role': 'assistant', 'content': '抱歉，我作为一个AI分身是无法提供金钱支持的。不过，如果有什么其他方面我可以帮忙的，尽管开口。'})
    message_handler = lambda x:analyze_chat(x, openai_client=openai_client(config), chat_model=config["OpenAI"]["chat_model"], response_format="text")
    chat.process_message('我现在生活真的很难，可以借我些钱吗？', message_handler, lambda x: print('Response: ' + x))
    chat.process_message('真的，我现在需要钱，你知道我的生活现在是什么状况吗？', message_handler, lambda x: print('Response: ' + x))
    chat.process_message('你明天在家吗，我想当面跟你说？', message_handler, lambda x: print('Response: ' + x))

    # 输出当前聊天历史
    print("Current chat history:", chat.get_history())

    # 模拟等待，查看聊天是否过期（这里使用较短的等待时间来演示）
    print("Waiting for chat to expire...")
    time.sleep(15)  # 这里时间应与 Chat 类中定义的 lifespan 相关，这里假设为短时间演示

    # 检查聊天是否还活跃
    if not chat.is_active():
        print(f"Chat for {user_id} has expired.")
    else:
        print(f"Chat for {user_id} is still active.")

    # 再次获取聊天历史
    print("Chat history after waiting:", chat.get_history())

if __name__ == "__main__":
    test()