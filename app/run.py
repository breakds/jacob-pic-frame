import os
import time

image_list = [
    '/home/breakds/Pictures/1.jpg',
    '/home/breakds/Pictures/2.jpg'
]

if __name__ == '__main__':
    while True:
        for image in image_list:
            os.system('DISPLAY=:0.0 feh -x {}&'.format(image))
            time.sleep(3.0)
            os.system('pkill feh')
            
