class StatBuffer:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.users: dict[int, dict] = {}
        self.chats: dict[int, dict] = {}
        self.members: set[tuple[int, int]] = set() # chat_id, user_id


    def swap(self) -> tuple[list[dict], dict[int, dict], dict[int, dict], set[tuple[int, int]]]:
        old = (self.messages, self.users, self.chats, self.members)
        self.messages, self.users, self.chats, self.members = [], {}, {}, set()

        return old

    def restore(self, old: tuple) -> None:
        """Вернуть данные в буфер, если запись в БД упала."""
        messages, users, chats, members = old
        self.messages = messages + self.messages
        self.users = {**users, **self.users}
        self.chats = {**chats, **self.chats}
        self.members |= members

buffer = StatBuffer()