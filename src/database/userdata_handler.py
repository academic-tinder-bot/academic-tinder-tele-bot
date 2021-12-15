import json
from typing import Dict

#TODO: encrypt with from cryptography.fernet import Fernet
jsonFilePath = "src/database/userdata/userCredentialsData.json"

def registerUser(name: str, handle: str, chatid: int) -> None:
    userData = json.load(open(jsonFilePath))
   
    userData[str(chatid)] = {
        "name": name,
        "handle": handle
    }
    

    open(jsonFilePath, "w").write(json.dumps(userData, indent=4))

def getUserData(chatid: int) -> Dict[str, str]:
    userData = json.load(open(jsonFilePath))
    return userData[str(chatid)]