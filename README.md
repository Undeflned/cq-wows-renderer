## cq-wows-renderer

A go-cqhttp bot generates minimap video from World of Warships replay file.

### Installation

1. Install & configure go-cqhttp, enable its http and websocket servers
2. Install Python 3.10
3. Clone the repo
    ```
    git clone —-recursive https://github.com/Undeflned/cq-wows-renderer.git & cd cq-wows-renderer
    ```
4. Create & activate a python virtual environment(using python, conda, etc.)
5. Install requirements
    ```
    (in venv)pip install -r requirements.txt
    ```
6. Copy & edit the config file
    ```
    cp config.default.json config.json & vim config.json
    ```

### Usage

+ Run the bot
    ```
    (in venv)python main.py
    ```
+ Use the renderer in group. (PM is not supported currently)
    ```
    #wows render
    ```
    or
    ```
    #wows dualrender
    ```

### License

This project is licensed under the GNU AGPLv3 License.

### Links

+ The renderer is based on WoWs-Builder-Team's [minimap-renderer](https://github.com/WoWs-Builder-Team/minimap_renderer).

+ go-cqhttp python api: FengLiuFeseliud's [pycqbot](https://github.com/FengLiuFeseliud/pycqBot)