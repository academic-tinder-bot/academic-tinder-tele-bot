import json
from typing import Dict, List, Union
from enum import Enum
#TODO: encrypt with from cryptography.fernet import Fernet


class UserSettingsJSONKeys(Enum):
    ALIAS = 'Alias'
class UserSettings:

    jsonFilePath = "src/database/userdata/user_config.json"

    @classmethod
    def addUser(cls, chatid: Union[int, str]):
        cls.readJSONData()
        cls.userSettings[str(chatid)]={}
        cls.writeJSONData()

    @classmethod
    def setAlias(cls, chatid: Union[int, str], alias: str = None) -> None:
        cls.readJSONData()
        if(not str(chatid) in cls.userSettings.keys()):
            cls.addUser(chatid)
        cls.userSettings[str(chatid)] = {
            UserSettingsJSONKeys.ALIAS.value: alias
        }
        cls.writeJSONData()

    @classmethod
    def getAlias(cls, chatid: Union[int, str]) -> str:
        cls.readJSONData()
        return cls.userSettings[str(chatid)][UserSettingsJSONKeys.ALIAS.value]

    @classmethod
    def readJSONData(cls) -> None:
        """Read the user data from the json file and store it in cls.userSettings"""
        try:
            cls.userSettings = json.load(open(cls.jsonFilePath))
        except json.decoder.JSONDecodeError:
            cls.initJSONData()
            cls.readJSONData()
    
    @classmethod
    def writeJSONData(cls) -> None:
        """Write the user data to the json file."""
        open(cls.jsonFilePath, "w").write(json.dumps(cls.userSettings, indent=4))
    
    @classmethod
    def initJSONData(cls) -> None:
        open(cls.jsonFilePath, "w").write(json.dumps({}))
if( __name__ == '__main__'):
    UserSettings.readJSONData()