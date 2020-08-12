import os
import time
import subprocess
import pathlib


class FrameEngine(object):
    def __init__(self):
        # TODO(breakds): Use enum instead
        self.video_player = 'mpv' # or 'omxplayer'
        self.image_viewer = 'feh'
        self.inherited_env = os.environ

    def play(self, path):
        if path.suffix.upper().endswith('JPG'):
            self.show_image(path)
        else:
            self.play_video(path)

    def play_video(self, path):
        proc = subprocess.run([
            self.video_player,
            '--fullscreen',
            path,
        ])

        if proc.returncode is not 0:
            print('Video player did not terminate peacefully.')


    def show_image(self, path):
        if self.image_viewer == 'feh':
            with subprocess.Popen(['feh', '-ZF', path]) as proc:
                time.sleep(3.0)
                proc.terminate()


def media_list_from_folder(folder):
    return [pathlib.Path(folder, f) for f in os.listdir(folder)]
            

if __name__ == '__main__':
    engine = FrameEngine()
    image_list = media_list_from_folder('/home/breakds/Downloads/qiu')
    while True:
        for image in image_list:
            print(image)
            engine.play(image)
            
