#!/usr/bin/env python3

from asyncio import subprocess
from icecream import ic
import cv2
from multiprocessing import Process, Queue
from subprocess import Popen, PIPE
from signal import pause

class Camera(Process):
    def __init__(self, v4l_cam_id: str = "/dev/video0", image_w_h: tuple = (1920,1080), window_name: str = "WebCam") -> None:
    
        self.process = super().__init__(target=self,daemon=True)
        self.q = Queue()
        self.img_w, self.img_h = image_w_h
        self.v4l_cam_id = v4l_cam_id
        self.cv_window_title = window_name
        self.cam_inst = None
        self._living_process = False
        
    def run(self):

        self.__connect()
        self.__configure_camera()
        self._living_process = True
        self.__framegrabber()
    
    def __connect(self):

        self.cam_inst = cv2.VideoCapture(self.v4l_cam_id)

    def __configure_camera(self):

        self.cam_inst.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc('M','J','P','G'))
        self.cam_inst.set(cv2.CAP_PROP_FRAME_WIDTH,self.img_w)
        self.cam_inst.set(cv2.CAP_PROP_FRAME_HEIGHT,self.img_h)

    def __new_frame(self):

        if self.is_alive() and self.cam_inst.isOpened(): rval, frame = self.cam_inst.read()
        else: rval = False; frame=None

        return rval,frame

    def __framegrabber(self):
        stat, frame = self.__new_frame()
        while stat and self._living_process: self.q.put(frame); stat, frame = self.__new_frame()

    def get_frame(self):
        return self.q.get()

    def preview(self):
        stat, frame = self.__new_frame()
        while self._living_process and stat:
            cv2.imshow(self.cv_window_title, frame)
            stat, frame = self.__new_frame()
            key = cv2.waitKey(20)
            if key == 27: # Esc key
                self.stop()
        
    def stop(self):
        self._living_process = False
        while self.q.qsize(): a=self.q.get()
        self.terminate()
        self.join()
        self.close()
            
        cv2.destroyWindow(self.cv_window_title)

def get_capture_devices():

    vid_proc = Popen(['ls /dev/video*'], shell=True, stdout=PIPE, encoding='UTF-8')
    devices=[x.split("\n")[0] for x in vid_proc.stdout.readlines()]
    capture_devices = []
    for device in devices:
        proc = Popen(f"udevadm info -n {device} | grep capture", shell=True, stdout=PIPE, encoding='UTF-8')
        if proc.stdout.readlines(): capture_devices.append(device)
    return capture_devices

if __name__ == "__main__":
    try:
        capture_devices = get_capture_devices()
        ic(capture_devices)
        webcams = [Camera(v4l_cam_id=device, window_name=device) for device in capture_devices]
        [x.start() for x in webcams]
        [x.preview() for x in webcams]

        pause()

    except KeyboardInterrupt:
        ic("Ending Program")
        [x.stop() for x in webcams]