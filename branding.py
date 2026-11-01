"""Selected C emblem, bundled in the one-file executable and shared across windows/tray."""
import sys
from pathlib import Path
import tkinter as tk

def asset_path(name):
 return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets'/name

def apply_window_icon(window):
 image=tk.PhotoImage(master=window,file=str(asset_path('Icon64.png')))
 window.iconphoto(True,image)
 if sys.platform=='win32':window.iconbitmap(default=str(asset_path('DeathAtlas.ico')))
 return image

def tray_image():
 from PIL import Image
 with Image.open(asset_path('Icon64.png')) as image:return image.convert('RGBA')
