from PIL import Image, ImageDraw
from pystray import Icon, MenuItem, Menu
import webbrowser
from pathlib import Path

from config.settings import general_settings


# アイコン用画像作成
def create_icon_image():
    image_path = Path('image') / 'logo.png'
    image = Image.open(image_path).convert('RGBA')
    image = image.resize((64, 64), Image.LANCZOS)
    return image


# pystrayタスク（同期関数）
port = general_settings.server_port
def create_tray_icon():
    def on_exit(icon, item):
        icon.stop()
    def open_console(icon, item):
        url = f"http://127.0.0.1:{port}"
        webbrowser.open(url)
        

    icon = Icon(
        'flexcc',
        title='flexcc',
        icon=create_icon_image(),
        menu=Menu(
            MenuItem('Open Console', open_console),
            MenuItem('Quit', on_exit)
        )
    )
    return icon