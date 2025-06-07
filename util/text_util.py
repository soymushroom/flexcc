import re
import html

pattern_hide = re.compile(r" *<hide>.*?</hide>(\n|)", flags=re.DOTALL)

# プレーンテキスト取得
def enable_hide_tag(text):
    return pattern_hide.sub("", text)

# プレーンテキスト取得
def get_plain_text(text):
    escaped_text = html.escape(enable_hide_tag(text))
    return f"<pre>{escaped_text}</pre>"