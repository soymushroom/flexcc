from PIL import Image, ImageDraw
from pystray import Icon, MenuItem, Menu
import webbrowser

from config.settings import preferences


# アイコン用画像作成
def create_icon_image():
    image = Image.new('RGB', (64, 64), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill='blue')
    return image


# pystrayタスク（同期関数）
port = preferences.ServerPort
def create_tray_icon():
    def on_exit(icon, item):
        icon.stop()
    def open_console(icon, item):
        url = f"http://127.0.0.1:{port}"
        webbrowser.open(url)
        

    icon = Icon(
        'test name',
        icon=create_icon_image(),
        menu=Menu(
            MenuItem('コンソールを開く', open_console),
            MenuItem('終了', on_exit)
        )
    )
    return icon