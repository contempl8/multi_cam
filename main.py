#!/usr/bin/env python3

from icecream import ic
import cv2
from multiprocessing import Process, Queue
from threading import Thread
from subprocess import Popen, PIPE
from signal import pause
import time
import click

class CameraNotFound(Exception):
    pass

class Camera(Process):
    def __init__(self, v4l_cam_id: int | str = "/dev/video0", image_w_h: tuple = (1920,1080), window_name: str = "WebCam", render_window:bool = True) -> None:
    
        super().__init__(target=self,daemon=True)
        self.q = Queue()
        self.img_w, self.img_h = image_w_h
        self.v4l_cam_id = v4l_cam_id
        self.cv_window_title = window_name
        self.cam_inst = None
        self._living_process = False
        self._render = render_window
        self.thread = Thread(target=self._framegrabber, daemon=True)
        self.time_then = time.time()
        self.count = 0
        
    def run(self):

        self._connect()
        self._configure_camera()
        self._living_process = True
        self.thread.start()
        if self._render: self.preview()
    
    def _connect(self):

        self.cam_inst = cv2.VideoCapture(self.v4l_cam_id)

    def _configure_camera(self):

        self.cam_inst.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc('M','J','P','G'))
        self.cam_inst.set(cv2.CAP_PROP_FRAME_WIDTH,self.img_w)
        self.cam_inst.set(cv2.CAP_PROP_FRAME_HEIGHT,self.img_h)

    def _new_frame(self):

        if self.is_alive() and self.cam_inst.isOpened(): rval, frame = self.cam_inst.read()
        else: rval = False; frame=None

        return rval,frame

    def _framegrabber(self):
        stat, frame = self._new_frame()
        while stat and self._living_process: self.q.put(frame); stat, frame = self._new_frame()

    def get_frame(self):
        return self.q.get()

    def preview(self):
        while self._living_process:
            frame = self.q.get()
            self.count+=1
            self._frames_per_sec()
            cv2.imshow(self.cv_window_title, frame)
            key = cv2.waitKey(20)
            if key == 27: # Esc key
                self.stop()

    def _frames_per_sec(self):
        time_now = time.time()
        time_diff = time_now - self.time_then
        if time_diff >= 5:
            fps = self.count / time_diff
            ic(f"fps: {fps}")
            self.count = 0
            self.time_then = time_now

    def stop(self):
        self._living_process = False
        if self.thread.is_alive: self.thread.join()
        while self.q.qsize(): a=self.q.get()
        self.close()
            
def get_capture_devices():

    vid_proc = Popen(['ls /dev/video*'], shell=True, stdout=PIPE, encoding='UTF-8')
    devices=[x.split("\n")[0] for x in vid_proc.stdout.readlines()]
    capture_devices = []
    for device in devices:
        proc = Popen(f"udevadm info -n {device} | grep capture", shell=True, stdout=PIPE, encoding='UTF-8')
        if proc.stdout.readlines(): capture_devices.append(device)
    return capture_devices

@click.group()
def cli():
    pass

@click.command()
@click.argument('print_framerate',type=click.BOOL,default=True)
def multiple_cameras(print_framerate):
        
    capture_devices = get_capture_devices()
    ic(capture_devices)
    if not len(capture_devices): raise CameraNotFound(ic("No Webcams Found"))
    webcams = [Camera(v4l_cam_id=device, window_name=device) for device in capture_devices]
    [x.start() for x in webcams]
    pause()

cli.add_command(multiple_cameras)

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        ic("Ending Program")