import httpx
from openai import OpenAI
import logging

def openai_client(config):
    """
    Initialize OpenAI client with proxy settings
    :param config: configuration dictionary
    """
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
    return openai_client