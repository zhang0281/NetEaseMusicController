# coding: utf-8

# https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html?highlight=pywinauto.keyboard.html#module-pywinauto.keyboard
# https://pywinauto.readthedocs.io/en/latest/HowTo.html#how-to-specify-a-usable-application-instance

import os

import psutil
from flask import Flask, request, jsonify
from pywinauto import Application

pause_play = "^P"
prev_song = "^{LEFT}"
next_song = "^{Right}"
volume_up = "^{UP}"
volume_down = "^{DOWN}"
like_song = "^L"

app = Flask(__name__)
project_root = os.path.abspath(".")
template = open(os.path.join(project_root, "templates/index.html"), "r", encoding="utf-8").read()


class MusicBox(object):

    @classmethod
    def check_if_running(cls, process_name):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == process_name:
                return True
        return False

    @classmethod
    def _press_keys(cls, keys):
        if cls.check_if_running(process_name='cloudmusic.exe'):
            # 自动从路径打开网易云音乐
            Application(backend="uia").start(r"C:\Program Files (x86)\NetEase\CloudMusic\cloudmusic.exe")
        # 连接打开网易云音乐的窗口
        app_connect = Application(backend='uia').connect(class_name="OrpheusBrowserHost")
        # 获取顶层窗口
        top_window = app_connect.top_window()
        # 输入指定按键
        top_window.type_keys(keys)

    @classmethod
    def next_song(cls):
        cls._press_keys(next_song)

    @classmethod
    def prev_song(cls):
        cls._press_keys(prev_song)

    @classmethod
    def pause_play(cls):
        cls._press_keys(pause_play)

    @classmethod
    def volume_up(cls):
        cls._press_keys(volume_up)

    @classmethod
    def volume_down(cls):
        cls._press_keys(volume_down)

    @classmethod
    def like_song(cls):
        cls._press_keys(like_song)

    # @classmethod
    # def shutdown(cls):
    #     os.system("shutdown -s -t 5")


@app.route('/')
def hello_world():
    key_word = request.args.get("action")
    if key_word:
        getattr(MusicBox, key_word)()

    return template


# 移动端连接服务器校验
@app.route('/mobile_connect')
def mobile_connect():
    response = jsonify(code=200, message="Connected", platform="win", status=1, version="0.0.1")
    response.status_code = 200
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10010)

