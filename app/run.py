import os
import time
import subprocess
import pathlib
import enum
import logging
import shutil
import random
import threading
import json
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
        # When set to true, the player will stop playing images or videos.
        self.stopped = False

    def allow_image(self):
        return self.media_format != MediaFormat.IMG_ONLY

    def allow_movie(self):
        return self.media_format != MediaFormat.MOV_ONLY

    def as_dict(self):
        return {
            'stopped': self.stopped,
            'loopType': self.loop_type.name,
            'mediaFormat': self.media_format.name,
            'imageDuration': self.image_duration,
        }



class Utility(object):
    global_config_lock = threading.Lock()
    global_config = FramePlayerConfig()

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
    def __init__(self, album_folder = None):
        # The FramePlayer runs a daemon thread so that when the signal
        # is received to kill the program, the program can gracefully
        # exit without waiting for this thread.
        threading.Thread.__init__(self, daemon = True)
        self.config = FramePlayerConfig()
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
            # Check whether there are new config available. If so, set
            # the config to the new config.
            try:
                locked = Utility.global_config_lock.acquire(blocking=False)
                self.config = Utility.global_config
            finally:
                if locked:
                    Utility.global_config_lock.release()
            if self.config.stopped:
                time.sleep(1.0)
                continue

            print('ok')
            time.sleep(1.0)

            # TODO(breakds): Process config update here.
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
    <script defer src="https://use.fontawesome.com/releases/v5.3.1/js/all.js" crossorigin="anonymous" SameSite="None"></script>
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.11"></script>
    <script>
      window.addEventListener("load", async envet => {
        const segments = window.location.href.split("/")
        const host = `${segments[0]}//${segments[2]}`;

        const response = await fetch(`${host}/getConfig`, {
          method: "POST",
          body: JSON.stringify({}),
        });
        const json = await response.json();
        const initial = {
          isSwitchBusy: false,
          isSubmitBusy: false,
          // TODO(breakds): Should make this a derived state. 
          // The current implementation is buggy (but tolerable).
          isModified: false,
          isStopped: json.stopped,
          mediaFormat: json.mediaFormat,
          imageDuration: json.imageDuration,
          loopType: json.loopType,
        };

        const app = new Vue({
          el: "#app",

          data() {
            return initial;
          },

          methods: {
            handleSwitchOnOff() {
              this.isSwitchBusy = true;
              fetch(`${host}/switch`, {
                method: "POST",
                body: JSON.stringify({}),
              }).then(response => {
                return response.json();
              }).then(json => {
                this.isSwitchBusy = false;
                this.isStopped = json.stopped;
              });
            },

            incDuration() {
              this.isModified = true;
              this.imageDuration = this.imageDuration + 1;
            },

            decDuration() {
              if (this.imageDuration > 3) {
                this.isModified = true;
                this.imageDuration = this.imageDuration - 1;
              }
            },

            setModified() {
              this.isModified = true;
            },

            async handleSubmit() {
              if (!this.isModified) {
                return;
              }
              this.isSubmitBusy = true;

              const response = await fetch(`${host}/setConfig`, {
                method: "POST",
                body: JSON.stringify({
                  stopped: this.isStopped,
                  mediaFormat: this.mediaFormat,
                  imageDuration: this.imageDuration,
                  loopType: this.loopType,
                }),
              });
              const json = await response.json();

              this.isSubmitBusy = false;
              this.isModified = false;
              this.isStopped = json.stopped;
              this.mediaFormat = json.mediaFormat;
              this.imageDuration = json.imageDuration;
              this.loopType = json.loopType;
            }
          },
        });
      });
    </script>
    <style>
      body { max-width: 800px; margin: auto; padding: 20px; }
    </style>
  </head>
  <body>
    <div id="app" class="container is-fullhd">
      <form v-on:submit.prevent>

        <div class="field is-horizontal">
          <div class="field-label is-normal">
            <label class="label">Switch</label>
          </div>
          <div class="field-body">
            <div class="field">
              <div class="control">
                <button v-if="isSwitchBusy"
                        class="button is-loading">Loading</button>
                <button v-else-if="isStopped"
                        v-on:click="handleSwitchOnOff"
                        class="button is-success">Start</button>
                <button v-else
                        v-on:click="handleSwitchOnOff"
                        class="button is-warning">Stop</button>
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
            <button class="button" v-on:click="decDuration">
              <span class="icon is-small">
                <i class="fas fa-minus"></i>
              </span>
            </button>
          </p>
          <p class="control">
            <input class="input" type="text" placeholder="Amount of money" 
                   disabled
                   v-bind:value="imageDuration + ' seconds'">
          </p>
          <p class="control">
            <button class="button" v-on:click="incDuration">
              <span class="icon is-small">
                <i class="fas fa-plus"></i>
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
                  <select v-model="loopType" v-on:change="setModified">
                    <option>ORDERED</option>
                    <option>RANDOM</option>
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
                  <select v-model="mediaFormat" v-on:change="setModified">
                    <option>IMG_ONLY</option>
                    <option>MOV_ONLY</option>
                    <option>BOTH</option>
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
                <button v-if="isSubmitBusy" class="button is-link is-loading" disabled>Loading</button>
                <button v-else-if="!isModified" class="button is-link" disabled>Submit</button>
                <button v-else class="button is-link" v-on:click="handleSubmit">Submit</button>
              </div>
            </div>
          </div>
        </div>

      </form>
    </div>
  </body>
</html>
"""

class ConfigPortal(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info('{}, {}'.format(self.path, self.headers))
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(CONFIG_PORTAL_WEBAPP.encode('utf-8'))

    def do_POST(self):
        if self.path not in ['/switch', '/getConfig', '/setConfig']:
            self.send_response(500)
            self.send_header('Content-type', 'html/text')
            self.end_headers()
            self.wfile.write('Unrecognized path {}'.format(self.path).encode('utf-8'))
            return

        updated_config = {}
        with Utility.global_config_lock:
            if self.path == '/switch':
                Utility.global_config.stopped = not Utility.global_config.stopped
            elif self.path == '/setConfig':
                print('Set Config!')
            updated_config = Utility.global_config.as_dict()

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(updated_config).encode('utf-8'))


if __name__ == '__main__':
    logger.info('Jacob Picture Frame started.')
    player = FramePlayer(album_folder = pathlib.Path(os.getenv('HOME'), 'Album'))
    player.start()

    with HTTPServer(('', 7500), ConfigPortal) as httpd:
        httpd.serve_forever()
