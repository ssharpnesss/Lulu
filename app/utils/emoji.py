from dataclasses import dataclass
import re

@dataclass
class TelegramEmoji:
    fallback: str
    emoji_id: str | None = None
    
    def __init__(self, fallback: str, emoji_id: str | None = None):
        if emoji_id:
            self.emoji_id = emoji_id
            self.fallback = fallback
        else:
            if "tg-emoji" in fallback:
                self.emoji_id = re.search(r"emoji-id=\"(\d+)\"", fallback).group(1)
                self.fallback = re.search(r">(.+?)<", fallback).group(1)
            else:
                self.emoji_id = None
                self.fallback = fallback

    def as_html(self) -> str:
        if self.fallback is None:
            return self.fallback
        return f'<tg-emoji emoji-id="{self.emoji_id}">{self.fallback}</tg-emoji>'

def get_emoji(emoji: str, as_html: bool = True):

    EMOJI_MAP = {
        "stats_emoji": TelegramEmoji('<tg-emoji emoji-id="5203993413346680064">📊</tg-emoji>'),
        "on_status": TelegramEmoji('<tg-emoji emoji-id="5323307196807653127">🟢</tg-emoji>'),
        "off_status": TelegramEmoji('<tg-emoji emoji-id="5323535839391653590">🔴</tg-emoji>')
    }

    r = EMOJI_MAP.get(emoji, None)

    if r is None:
        return "?"

    return r.as_html() if as_html else r.fallback