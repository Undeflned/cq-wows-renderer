from pycqBot import cqHttpApi
from bot import WOWSRendererBot
import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("config.json", "r") as f:
    config = json.load(f)

cqapi = cqHttpApi(host=config["http_host"], download_path=config["download_path"])
bot = WOWSRendererBot(cqapi, config)
bot.start(start_go_cqhttp=False)
