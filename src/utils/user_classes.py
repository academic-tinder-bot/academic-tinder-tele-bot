from utils.names import randomName

class User:

    def __init__(self, name: str, username: str, chatid: str) -> None:
        self.name = name
        self.username = username
        self.chatid = chatid

    @classmethod
    def fromDict(cls, dict: dict) -> None:
        return cls(dict["name"], dict["username"], dict["chatid"])

    def toDict(self):
        return {
            "name": self.name,
            "username": self.username,
            "chatid": self.chatid
        }

    def __eq__(self, x):
        return self.chatid == x.chatid

    def __str__(self) -> str:
        return self.toDict().__str__()

class AnonymousUser(User):
    def __init__(self, name: str, username: str, chatid: str) -> None:
        super().__init__(name, username, chatid)
        self.anonName = "Anon " + randomName()

    @classmethod
    def fromUser(cls, user: User) -> None:
        return cls(user.name, user.username, user.chatid)

    def toDict(self):
        return {
            "name": self.name,
            "username": self.username,
            "chatid": self.chatid,
            "anonName": self.anonName
        }

    def __str__(self) -> str:
        return self.toDict().__str__()
        