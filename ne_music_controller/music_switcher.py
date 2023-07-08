# coding: utf-8
import asyncio
import atexit
import json
import os
from io import BytesIO
import traceback
import winsdk.windows.media.control as wmc
from comtypes import CoInitialize, CoUninitialize
from flask import Flask, request, jsonify, send_file
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
from win32api import keybd_event
from win32con import VK_MEDIA_PLAY_PAUSE, VK_MEDIA_NEXT_TRACK, VK_MEDIA_PREV_TRACK, KEYEVENTF_EXTENDEDKEY
from winsdk.windows.storage.streams import (DataReader, Buffer, InputStreamOptions)
import logging
import io
import PIL.Image

app = Flask(__name__)
project_root = os.path.abspath(".")


class MusicBox(object):
    @classmethod
    def image2png(cls, rawdata):
        ''' convert an image to png '''

        if not rawdata:
            return None

        if rawdata.startswith(b'\211PNG\r\n\032\n'):
            logging.debug('already PNG, skipping convert')
            return rawdata

        try:
            imgbuffer = io.BytesIO(rawdata)
            logging.getLogger('PIL.TiffImagePlugin').setLevel(logging.CRITICAL + 1)
            logging.getLogger('PIL.PngImagePlugin').setLevel(logging.CRITICAL + 1)
            image = PIL.Image.open(imgbuffer)
            imgbuffer = io.BytesIO(rawdata)
            if image.format != 'PNG':
                image.convert(mode='RGB').save(imgbuffer, format='PNG')
        except Exception as error:  # pylint: disable=broad-except
            logging.debug(error)
            return None
        logging.debug("Leaving image2png")
        return imgbuffer.getvalue()

    @classmethod
    async def _getcoverimage(cls, thumbref):
        ''' read the thumbnail buffer '''
        try:
            thumb_read_buffer = Buffer(5000000)

            readable_stream = await thumbref.open_read_async()
            await readable_stream.read_async(thumb_read_buffer, thumb_read_buffer.capacity,
                                       InputStreamOptions.READ_AHEAD)
            buffer_reader = DataReader.from_buffer(thumb_read_buffer)
            if byte_buffer := bytearray(
                    buffer_reader.read_buffer(buffer_reader.unconsumed_buffer_length)):
                return cls.image2png(byte_buffer)
        except:  # pylint: disable=bare-except
            for line in traceback.format_exc().splitlines():
                logging.error(line)
        return None

    @classmethod
    async def get_media_info(cls):
        sessions = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()

        # This source_app_user_model_id check and if statement is optional
        # Use it if you want to only get a certain player/program's media
        # (e.g. only chrome.exe's media not any other program's).

        # To get the ID, use a breakpoint() to run sessions.get_current_session()
        # while the media you want to get is playing.
        # Then set TARGET_ID to the string this call returns.

        global current_session
        current_session = sessions.get_current_session()
        if current_session:  # there needs to be a media session running
            if current_session.source_app_user_model_id.startswith('cloudmusic'):
                info = await current_session.try_get_media_properties_async()

                # song_attr[0] != '_' ignores system attributes
                info_dict = {song_attr: info.__getattribute__(song_attr) for song_attr in dir(info) if
                             song_attr[0] != '_'}

                # converts winrt vector to list
                info_dict['genres'] = list(info_dict['genres'])

                return info_dict

        # It could be possible to select a program from a list of current
        # available ones. I just haven't implemented this here for my use case.
        raise Exception('TARGET_PROGRAM is not the current media session')

    @classmethod
    def get_info(cls):
        data = asyncio.run(cls.get_media_info()).copy()
        del data['thumbnail']
        return json.dumps(data)

    @classmethod
    async def get_info_pic(cls):

        thumbnail = (await cls.get_media_info())['thumbnail']
        result = await cls._getcoverimage(thumbnail)
        return send_file(BytesIO(result), mimetype='image/png')

    @classmethod
    def get_pic(cls):
        return asyncio.run(cls.get_info_pic())

    @classmethod
    def media_is(cls, state):
        if current_session is None:
            return False
        # CHANGING CLOSED OPENED PAUSED PLAYING STOPPED
        return int(wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus[
                       state]) == current_session.get_playback_info().playback_status  # get media state enum and compare to current main media session state

    @classmethod
    def next_song(cls):
        keybd_event(VK_MEDIA_NEXT_TRACK, 0, KEYEVENTF_EXTENDEDKEY, 0)

    @classmethod
    def prev_song(cls):
        keybd_event(VK_MEDIA_PREV_TRACK, 0, KEYEVENTF_EXTENDEDKEY, 0)

    @classmethod
    def pause_play(cls):
        keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY, 0)

    @classmethod
    def vol_slider(cls, arg):
        if isinstance(arg, str):
            arg = float(arg)
        CoInitialize()
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            if session.Process and session.Process.name().startswith("cloudmusic"):
                print("cloudmusic volume: %s" % str(round(volume.GetMasterVolume(), 2)))
                volume.SetMasterVolume(arg, None)
        CoUninitialize()

    @classmethod
    def get_vol(cls):
        CoInitialize()
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            if session.Process and session.Process.name().startswith("cloudmusic"):
                return round(volume.GetMasterVolume(), 2)
        CoUninitialize()


@app.route('/')
def hello_world():
    key_word = request.args.get("action")
    arg = request.args.get("arg")
    result = None
    if key_word:
        if arg:
            result = getattr(MusicBox, key_word)(arg)
        else:
            result = getattr(MusicBox, key_word)()
    if result is not None:
        if isinstance(result, float) or isinstance(result, dict) :
            return str(result)
        return result
    else:
        template = open(os.path.join(project_root, "templates/index.html"), "r", encoding="utf-8").read()
        return template


# 移动端连接服务器校验
@app.route('/mobile_connect')
def mobile_connect():
    response = jsonify(code=200, message="Connected", platform="win", status=1, version="0.0.1")
    response.status_code = 200
    return response


if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host="0.0.0.0", port=10010,debug=True)


def restore_volume():
    MusicBox.vol_slider(1)


atexit.register(restore_volume)
