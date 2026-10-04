from typing import Iterable, Optional, Union
import re

from aiogram.filters import BaseFilter
from aiogram.types import Message
from babel.support import LazyProxy


class LuluFilter(BaseFilter):
    def __init__(
        self,
        command: Optional[Union[str, LazyProxy, Iterable[Union[str, LazyProxy]]]] = None,
        ignore_case: bool = True,
        is_equals: bool = False,
        ignore_name: bool = False,
    ):
        names = ["лу", "лулу", "лу-лу", "lu", "lulu", "lu-lu"]
        self.default_name = names + [f"{name}," for name in names]
        commands = [command] if isinstance(command, (str, LazyProxy)) else command
        self.command = tuple(commands or ())
        self.ignore_case = ignore_case
        self.is_equals = is_equals
        self.ignore_name = ignore_name

    async def __call__(self, message: Message):
        text = message.text or ""
        tokens = list(re.finditer(r"\S+", text))
        parts = [token.group() for token in tokens]
        if not parts:
            return False
        normalize = str.casefold if self.ignore_case else str
        candidates = [(parts, 0)] if self.ignore_name else []
        if normalize(parts[0]) in self.default_name:
            candidates.append((parts[1:], 1))
        for candidate, name_length in candidates:
            for command in self.command:
                command_parts = str(command).split()
                length = len(command_parts)
                if not length or len(candidate) < length:
                    continue
                if self.is_equals and len(candidate) != length:
                    continue
                if list(map(normalize, candidate[:length])) == list(map(normalize, command_parts)):
                    consumed = name_length + length
                    offset = tokens[consumed].start() if consumed < len(tokens) else len(text)
                    return {
                        "lulu_args": candidate[length:],
                        "lulu_text": text[offset:],
                        "lulu_text_offset": offset,
                    }
        return False
