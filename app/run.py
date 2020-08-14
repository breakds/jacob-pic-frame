import os
import time
import subprocess
import pathlib
import enum
import logging
import shutil
import random

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


class FramePlayer(object):
    def __init__(self, config = None, album_folder = None):
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

    def run_and_block(self):
        # TODO(breakds): Find a better solution for the transition
        # problem, e.g. double buffer.
        blank_bg_path = pathlib.Path(os.getenv('HOME'), '.jpframe', 'blank.jpg')
        background_proc = subprocess.Popen(['feh', '-ZF', '--hide-pointer', blank_bg_path])
        while True:
            # TODO(breakds): Process album change and config update here.
            if len(self.album) == 0:
                time.sleep(1.0)
                continue

            self.play_single_media(self.album[self.current_index])

            if self.config.loop_type is LoopType.ORDERED:
                step = 1
            else:
                step = random.randrange(1, len(self.album))
            self.current_index = (self.current_index + step) % len(self.album)
        background_proc.terminate()


if __name__ == '__main__':
    logger.info('Jacob Picture Frame started.')
    player = FramePlayer(album_folder = pathlib.Path(os.getenv('HOME'), 'Album'))
    player.run_and_block()
