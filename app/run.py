import os
import time
import subprocess
import pathlib
import enum
import logging
import shutil
import random
import threading

from http.server import HTTPServer, BaseHTTPRequestHandler

# TODO(breakds): Embed a web service in it.
# Following https://paste.readthedocs.io/en/latest/do-it-yourself-framework.html

logging.basicConfig(format='%(asctime)s %(name)s [%(levelname)s]: %(message)s')
logger = logging.getLogger('JPFrame')
logger.setLevel(logging.INFO)


class LoopType(enum.Enum):
    ORDERED = 1
    RANDOM = 2


class MediaFormat(enum.Enum):
    BOTH = 1
    MOV_ONLY = 2
    IMG_ONLY = 3


class FramePlayerConfig(object):
    def __init__(self):
        self.loop_type = LoopType.ORDERED
        self.media_format = MediaFormat.BOTH
        # The duration that each image gets displayed before the player switches
        # to the next media.
        self.image_duration = 10.0

    def allow_image(self):
        return self.media_format != MediaFormat.IMG_ONLY

    def allow_movie(self):
        return self.media_format != MediaFormat.MOV_ONLY


class Utility(object):
    @staticmethod
    def check_program_installed(program):
        return program if shutil.which(program) else None

    @staticmethod
    def ensure_video_player():
        """Return the video player command to use.

        Return None if neigther omxplayer and mpv exist.
        """
        return (Utility.check_program_installed('omxplayer') or
                Utility.check_program_installed('mpv'))

    @staticmethod
    def ensure_image_viewer():
        """Return the image viewer command to use

        Currently it only supports feh, and if feh does not exist, return None instead.
        """
        return Utility.check_program_installed('feh')

    @staticmethod
    def make_album(album_folder):
        return [pathlib.Path(album_folder, f)
                for f in os.listdir(album_folder)]


class FramePlayer(threading.Thread):
    def __init__(self, config = None, album_folder = None):
        # The FramePlayer runs a daemon thread so that when the signal
        # is received to kill the program, the program can gracefully
        # exit without waiting for this thread.
        threading.Thread.__init__(self, daemon = True)
        self.config = config if config is not None else FramePlayerConfig()
        # TODO(breakds): Find a better solution to find a default
        # album if album_folder is None
        self.album = Utility.make_album(album_folder)
        # The index of the media file in the album (which is a list of paths)
        # that is being played.
        self.current_index = 0
        self.video_player = Utility.ensure_video_player()
        if self.video_player is None:
            raise Exception('Cannot find usable video player (omxplayer or mpv).')
        self.image_viewer = Utility.ensure_image_viewer()
        if self.image_viewer is None:
            raise Exception('Cannot find usable image viewer (feh).')

    def play_single_media(self, path):
        if not path.exists():
            logger.warning('Skipping nonexistent file: {}'.foramt(path))
            return
        if path.is_dir():
            logger.warning('Skipping folder: {}'.format(path))
            return

        media_type = path.suffix.upper()


        if media_type in ['.JPG', '.PNG', '.JPEG']:
            if self.config.allow_image():
                self.show_image(path, self.config.image_duration)
        elif media_type in ['.MOV', '.MP4']:
            if self.config.allow_movie():
                self.play_video(path)
        else:
            logger.warning('Media type [{}] not recognized: {}'.format(media_type, path))

    def play_video(self, path):
        if self.video_player == 'mpv':
            proc = subprocess.run(['mpv', '--fullscreen', path])
            if proc.returncode is not 0:
                logger.warning('Failed to play movie: {}'.format(path))
        elif self.video_player == 'omxplayer':
            proc = subprocess.run(['omxplayer', path])
            if proc.returncode is not 0:
                logger.warning('Failed to play movie with omxplayer: {}'.format(path))

    def show_image(self, path, image_duration):
        if self.image_viewer == 'feh':
            with subprocess.Popen([
                    'feh', '-ZF', '--auto-rotate', '--hide-pointer',
                    path]) as proc:
                time.sleep(image_duration)
                proc.terminate()

    def run(self):
        # TODO(breakds): Find a better solution for the transition
        # problem, e.g. double buffer.
        blank_bg_path = pathlib.Path(os.getenv('HOME'), '.jpframe', 'blank.jpg')
        background_proc = subprocess.Popen(['feh', '-ZF', '--hide-pointer', blank_bg_path])
        while True:
            print('ok')
            time.sleep(1.0)
            # # TODO(breakds): Process album change and config update here.
            # if len(self.album) == 0:
            #     time.sleep(1.0)
            #     continue

            # self.play_single_media(self.album[self.current_index])

            # if self.config.loop_type is LoopType.ORDERED:
            #     step = 1
            # else:
            #     step = random.randrange(1, len(self.album))
            # self.current_index = (self.current_index + step) % len(self.album)
        background_proc.terminate()


CONFIG_PORTAL_WEBAPP = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Jacob Picture Frame Config Portal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.0/css/bulma.min.css">
    <script defer src="https://use.fontawesome.com/releases/v5.3.1/js/all.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.11"></script>
    <script>
    </script>
    <style>
      body { max-width: 800px; margin: auto; padding: 20px; }
    </style>
  </head>
  <body>
    <div id="app" class="container is-fullhd">
      <form>
        
        <div class="field is-horizontal">
          <div class="field-label">
            <label class="label">On/Off</label>
          </div>
          <div class="field-body">
            <div class="field">
              <div class="control">
                <label class="radio"><input type="radio" name="question"> Play </label>
                <label class="radio"><input type="radio" name="question"> Stop </label>
              </div>
            </div>
          </div>
        </div>

        <div class="field is-horizontal">
          <div class="field-label is-normal">
            <label class="label">Display Time</label>
          </div>
          <div class="field-body">
        <div class="field has-addons">
          <p class="control">
            <button class="button">
              <span class="icon is-small">
                <i class="fas fa-bold"></i>
              </span>
            </button>
          </p>
          <p class="control">
            <input class="input" type="text" placeholder="Amount of money">
          </p>
          <p class="control">
            <button class="button">
              <span class="icon is-small">
                <i class="fas fa-bold"></i>
              </span>
            </button>
          </p>
        </div>
          </div>
        </div>

        <div class="field is-horizontal">
          <div class="field-label">
            <label class="label">Loop Type</label>
          </div>
          <div class="field-body">
            <div class="field">
              <div class="control">
                <div class="select">
                  <select>
                    <option>Select dropdown</option>
                    <option>With options</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="field is-horizontal">
          <div class="field-label">
            <label class="label">Media Type</label>
          </div>
          <div class="field-body">
            <div class="field">
              <div class="control">
                <div class="select">
                  <select>
                    <option>Select dropdown</option>
                    <option>With options</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>


        <div class="field is-horizontal">
          <div class="field-label">
            <label class="label"></label>
          </div>
          <div class="field-body">
            <div class="field">
              <div class="control">
                <button class="button is-link">Submit</button>
              </div>
            </div>
          </div>
        </div>

      </form>
    </div>
  </body>
</html>
"""

class ConfigProtal(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info('{}, {}'.format(self.path, self.headers))
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(CONFIG_PORTAL_WEBAPP.encode('utf-8'))

if __name__ == '__main__':
    logger.info('Jacob Picture Frame started.')
    player = FramePlayer(album_folder = pathlib.Path(os.getenv('HOME'), 'Album'))
    player.start()

    with HTTPServer(('', 7500), ConfigProtal) as httpd:
        httpd.serve_forever()
