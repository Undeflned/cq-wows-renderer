from pycqBot import cqHttpApi, cqBot
from pycqBot.cqHttpApi import Message, Notice_Event
from pycqBot.data.event import Notice_Event
from render import render_single, render_dual
from pathlib import Path
from os import remove, listdir
from concurrent.futures import ProcessPoolExecutor
from asyncio import wrap_future
from threading import Lock
import asyncio
import logging






class WOWSRendererBot(cqBot):
    def __init__(self, cqapi: cqHttpApi, config: dict):
        super().__init__(cqapi, config['ws_host'], config['group_id_list'], config['user_id_list'], config['bot_options'])
        self.config = config
        self.cqapi.download_end = self.download_end
        self.renderPool = ProcessPoolExecutor(self.config['max_render_processes'])
        self.renderQueue = {}
        self.queueLock = Lock()
        self.WAITING_FOR_UPLOAD = 0
        self.DOWNLOADING = 1
        self.WAITING_FOR_UPLOAD_DUAL = 2
        self.WAITING_FOR_UPLOAD_SECOND = 3
        self.help_text_format: str = "{help_command_text}"
        self._set_command_key = self._set_command_key_fix
        for file in listdir(self.cqapi._download_path):
            remove(str(Path(self.cqapi._download_path).joinpath(file)))


        def wows(_, msg: Message):
            helpText = self.commandSign + "wows render - render a replay\n" + self.commandSign + "wows dualrender - render replays from two teams in one video\n"
            if msg.sub_type != "normal":
                return
            if len(_) == 0:
                self.cqapi.send_group_msg(msg.event.data['group_id'], helpText)
                return
            match _[0]:
                case "render":
                    with self.queueLock:
                        if len(self.renderQueue) >= self.config['max_render_processes']:
                            msg.reply("The queue is full, please wait for a while")
                            return
                        if str(msg.sender.id) not in self.renderQueue:
                            msg.reply("Please upload the replay file in {} seconds.(Ends with .wowsreplay)".format(self.config['user_upload_timeout']))
                            self.renderQueue[str(msg.sender.id)] = [self.WAITING_FOR_UPLOAD]
                            self.cqapi.add_task(self.timer(str(msg.sender.id), self.WAITING_FOR_UPLOAD, self.config['user_upload_timeout']))
                case "dualrender":
                    with self.queueLock:
                        if len(self.renderQueue) >= self.config['max_render_processes']:
                            msg.reply("The queue is full, please wait for a while")
                            return
                        if str(msg.sender.id) not in self.renderQueue:
                            msg.reply("Please upload the first replay file in {} seconds.(Ends with .wowsreplay)".format(self.config['user_upload_timeout']))
                            self.renderQueue[str(msg.sender.id)] = [self.WAITING_FOR_UPLOAD_DUAL]
                            self.cqapi.add_task(self.timer(str(msg.sender.id), self.WAITING_FOR_UPLOAD_DUAL, self.config['user_upload_timeout']))
                case _:
                    self.cqapi.send_group_msg(msg.event.data['group_id'], helpText)
        

        self.command(wows,"wows",{
            "type": "group",
            "help": [self.commandSign + "wows - WOWS replay renderer"],
            })
        

    def notice_group_upload(self, event: Notice_Event):
        if event.data['file']['name'].endswith(".wowsreplay") and str(event.data['user_id']) in self.renderQueue:
            match self.renderQueue[str(event.data['user_id'])][0]:
                case self.WAITING_FOR_UPLOAD:
                    self.renderQueue[str(event.data['user_id'])][0] = self.DOWNLOADING
                    self.cqapi.send_group_msg(event.data['group_id'], "Rendering {}...".format(event.data['file']['name']), auto_escape=True)
                case self.WAITING_FOR_UPLOAD_DUAL:
                    self.renderQueue[str(event.data['user_id'])][0] = self.WAITING_FOR_UPLOAD_SECOND
                    self.cqapi.send_group_msg(event.data['group_id'], "Please upload the second replay file in {} seconds.(Ends with .wowsreplay)".format(self.config['user_upload_timeout']))
                    self.cqapi.add_task(self.timer(str(event.data['user_id']), self.WAITING_FOR_UPLOAD_SECOND, self.config['user_upload_timeout']))
                case self.WAITING_FOR_UPLOAD_SECOND:
                    self.renderQueue[str(event.data['user_id'])][0] = self.DOWNLOADING
                    self.cqapi.send_group_msg(event.data['group_id'], "Rendering {} + {}...".format(self.renderQueue[str(event.data['user_id'])][1], event.data['file']['name']), auto_escape=True)
                case _:
                    return
            
            self.renderQueue[str(event.data['user_id'])].append(event.data['file']['name'])
            download_name = "{}.{}.{}".format(event.data['group_id'], event.data['user_id'], event.data['file']['name'])
            logging.info("Found replay file {} send by {} from group {}, downloading".format(event.data['file']['name'], event.data['user_id'], event.data['group_id']))
            self.cqapi.download_file(download_name, event.data['file']['url'])
    

    def download_end(self, file_name: str, file_url: str, code: int):
        logging.info("%s 下载完成! code: %s" % (file_name, code))
        if code == 200 and file_name.endswith(".wowsreplay"):
            group_id, user_id = file_name.split('.')[0:2]
            if self.renderQueue[user_id][0] == self.DOWNLOADING:
                logging.info("Replay file {} downloaded, rendering".format(file_name))
                self.cqapi.add_task(self.render_and_upload(group_id, user_id))
    

    async def render_and_upload(self, group_id: str, user_id: str):
        download_prefix = str(Path(self.cqapi._download_path).joinpath(group_id + '.' + user_id + '.'))
        match len(self.renderQueue[user_id]):
            case 2:
                full_path = download_prefix + self.renderQueue[user_id][1]
                upload_name = Path(self.renderQueue[user_id][1]).stem + '.mp4'
                rendered = await wrap_future(self.renderPool.submit(render_single, full_path))
            case 3:
                full_path = [download_prefix + self.renderQueue[user_id][1], download_prefix + self.renderQueue[user_id][2]]
                upload_name = Path(self.renderQueue[user_id][1]).stem + '+' + Path(self.renderQueue[user_id][2]).stem + '.mp4'
                rendered = await wrap_future(self.renderPool.submit(render_dual, full_path[0], full_path[1]))
            case _:
                raise ValueError("Invalid queue item(s)")
        del self.renderQueue[user_id]

        if rendered[0]:
            self.cqapi.send_group_msg(group_id, "Failed when rendering {}: {}".format(upload_name, rendered[1]), auto_escape=True)
            logging.warning("Failed when rendering {}: {}, cleaning up".format(upload_name, rendered[1]))
            if isinstance(full_path, list):
                for path in full_path:
                    remove(path)
            else:
                remove(full_path)
            return
        
        logging.info("{} completed, uploading".format(upload_name))
        self.cqapi.upload_group_file(group_id, rendered[1], upload_name, '')
        for i in range(self.config['upload_timeout'] // self.config['upload_sleep_time']):
            await asyncio.sleep(self.config['upload_sleep_time'])
            for file in self.cqapi.get_group_root_files(group_id.split('.')[0])['data']['files']:
                if file['file_name'] == upload_name:
                    logging.info("Upload {} complete, cleaning up".format(upload_name))
                    if isinstance(full_path, list):
                        for path in full_path:
                            remove(path)
                    else:
                        remove(full_path)
                    remove(rendered[1])
                    return
        logging.warning("Upload {} timeout, cleaning up".format(upload_name))
        if isinstance(full_path, list):
            for path in full_path:
                remove(path)
        else:
            remove(full_path)
        remove(rendered[1])
    

    async def timer(self, key: str, status, timeout: int):
        await asyncio.sleep(timeout)
        if key in self.renderQueue and self.renderQueue[key][0] == status:
            del self.renderQueue[key]
            logging.info("User {} timeout".format(key))


    def _set_command_key_fix(self, message: str):
        """
        指令解析
        """
        if len(message) == 0:
            return "", "", []
        if self.commandSign != "":
            commandSign = list(message)[0]
        else:
            commandSign = ""

        command_str_list = message.split(" ")
        command = command_str_list[0].lstrip(commandSign)
        commandData = command_str_list[1:]

        return commandSign, command, commandData


