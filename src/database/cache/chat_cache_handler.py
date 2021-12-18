import json
from typing import Dict, List


class ChatCacheHandler:
    """
    The json file format is:
    {
        <userid>:{
            <user(that sent the message)> : [<message1>, <message2>, ...]
        }
    }
    Messages are added on to the file as a queue using append(), and then when called,
    and then removed in order of left to right.
    """
    CACHE_DATA: Dict[str, Dict[str, List[str]]]= {}

    @classmethod
    def get_cache_data(cls):
        """
        Get the cache data from the json file.
        """
        cls.CACHE_DATA = json.load(open("src/database/cache/chatCache.json"))

    @classmethod
    def write_cache_data(cls):
        """
        Write the cache data to the json file.
        """
        json.dump(cls.CACHE_DATA, open("src/database/cache/chatCache.json", "w"))

    @classmethod
    def addUser(cls, userid: str):
        """Add an empty user to the cache. Does nothing if the user is already in the cache."""
        cls.get_cache_data()
        if(userid in cls.CACHE_DATA.keys()):
            return
        cls.CACHE_DATA[userid] = {}
        cls.write_cache_data()
    
    @classmethod
    def deleteUser(cls, userid: str):
        """Delete a user (dict) from the cache. Does nothing if the user is not in the cache."""
        if(not userid in cls.CACHE_DATA.keys()):
            return
        cls.CACHE_DATA.pop(userid)
        cls.write_cache_data()

    @classmethod
    def getAllMessages(cls, userid: str) -> Dict[str, List[str]]:
        """Get the list of user messages.
        Returns a dict of list (queue) of user messages.
        After getting the messages, iterate through them with a for loop, instead of popping the list."""
        return cls.CACHE_DATA[userid]

    @classmethod
    def getMessagesFromUser(cls, recepient: str, sender: str) -> List[str]:
        """Get the list of user messages from a specific user.
        Returns a list (queue) of user messages.
        After getting the messages, iterate through them with a for loop, instead of popping the list."""
        return cls.CACHE_DATA[recepient][sender]

    @classmethod
    def popAllMessages(cls, userid: str) -> Dict[str, List[str]]:
        """Returns a list of user messages.
        Deletes the queue (dict object, in fact) of the cache.
        After getting the messages, iterate through them with a for loop, instead of popping the list."""
        messages = cls.getAllMessages(userid)
        cls.deleteUser(userid)
        cls.write_cache_data()
        return messages

    @classmethod
    def popMessagesFromUser(cls, recepient: str, sender: str) -> List[str]:
        """Returns the list of user messages from a specific user.
        Returns a list (queue) of user messages. Deletes the list.
        After getting the messages, iterate through them with a for loop, instead of popping the list."""
        try:
            messages = cls.CACHE_DATA[recepient][sender]
            cls.CACHE_DATA[recepient].pop(sender)
            cls.write_cache_data()
        except KeyError: 
            messages = []
        return messages

    @classmethod
    def addChatMessage(cls, recepient: str, sender: str, message: str):
        """Appends a new message to the end of the cache. Tries to add a user, in case the user does not exist."""
        cls.addUser(recepient)
        try:
            cls.CACHE_DATA[recepient][sender].append(message)
            print(cls.CACHE_DATA[recepient][sender])
        except KeyError:
            cls.CACHE_DATA[recepient][sender] = []
            cls.CACHE_DATA[recepient][sender].append(message)
            print(cls.CACHE_DATA[recepient][sender])
        cls.write_cache_data()
    
    @classmethod
    def countUnreadMessages(cls, recepient: str) -> Dict[str, int]:
        """Returns a dictionary that counts all unread messages, with 
        key = sender, value = message count"""
        returnDict = {}
        for (sender, messages) in cls.getAllMessages(recepient).items():
            returnDict[sender] = len(messages)
        return returnDict

if (__name__ == "__main__"):
    cache = ChatCacheHandler()

    me = "474531382"
    them = "1887930239"
    cache.addUser(me)
    cache.addUser(them)

    cache.addChatMessage(me, them, "Hello, test")
    cache.addChatMessage(me, them, "Hello, test2")
    cache.addChatMessage(me, them, "Hello, test3")

    # print(cache.get_user_messages(user1))
    # print(cache.popAllMessages(user1))
ChatCacheHandler.get_cache_data()