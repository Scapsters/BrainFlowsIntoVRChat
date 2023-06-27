import threading
import math
import time

from tkinter import *
from PIL import ImageTk, Image


class hexVisualThread(threading.Thread):
    def __init__(self, side=600, wait_seconds=1/60):
        threading.Thread.__init__(self)
        self.side = side
        self.wait_seconds = wait_seconds
        self.alpha = 1.0
        self.target_alpha = 1.0
        self.img = None

    def update_alpha(self, alpha):
        self.target_alpha = alpha

    def run(self):
        # Create an instance of tkinter window
        win = Tk()

        # Define the geometry of the window
        win.geometry("{}x{}".format(self.side, self.side))

        canvas = Canvas(win, width=self.side, height=self.side)
        canvas.configure(bg="black")

        # Create an object of tkinter ImageTk
        size = (self.side, self.side)

        original = Image.open("HexHeartInvert.png")
        original = original.resize(size)

        while True:
            canvas.delete("all")

            weight = 0.3
            self.alpha = self.target_alpha * \
                weight + self.alpha * (1.0 - weight)

            sm_side = math.ceil(self.side * self.alpha)
            pil_img = original \
                .resize((sm_side, sm_side), resample=Image.BILINEAR) \
                .resize(size, resample=Image.NEAREST)
            self.img = ImageTk.PhotoImage(pil_img)

            canvas.create_image(0, 0, anchor=NW, image=self.img)
            canvas.pack(fill="both", expand=True)
            win.update()

            time.sleep(self.wait_seconds)


if __name__ == "__main__":
    t = hexVisualThread()
    t.start()
    t.update_alpha(0.2)
    t.join()
