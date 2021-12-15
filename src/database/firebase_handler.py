
from __future__ import annotations
from logging import error


from threading import current_thread
from typing import Dict, List
import firebase_admin
from firebase_admin import credentials, firestore

# from utils.user_classes import User


class FireStoreManager:

    instance: FireStoreManager

    def __init__(self) -> None:
        self.cred = credentials.Certificate(
            "src\keys\makerthon-2022-9a97e-firebase-adminsdk-qniun-0539fb076e.json")
        firebase_admin.initialize_app(self.cred)

        self.db = firestore.client()  # this connects to our Firestore database
        FireStoreManager.instance = self
        self.moduleToUserCollection = self.db.collection(
            'Module-to-User')  # opens 'module-to-user' collection
        self.userToModuleCollection = self.db.collection("User-to-Module")

        self.userToUserCollection = self.db.collection("User-to-User")

    @classmethod
    def getInstance(cls) -> FireStoreManager:
        return cls.instance

    ########## User-to-Module and Module-to-User DB ##########
    def unregisterModule(self, modulecode: str):
        """
        TODO: Removes module from both module-to-user and user-to-module databases. Removes user purely by module code.
        """

    def updateUserModuleList(self, chatid: int, moduleCodeList: List[str]):
        """Updates the module list of the user to the list given. Updates two databases:
        1. module-to-user database
        2. user-to-module database

        How it works is that removes the relevant user-module from the DB, then updates the user module list."""

        currentModuleList = self.getModulesfromUser(chatid=chatid)

        # Remove modules
        for module in currentModuleList:
            if(not module in moduleCodeList):
                self.removeModuleFromUser(chatid=chatid, moduleCode=module)

        # Set new module list
        self.userToModuleCollection.document(str(chatid)).set({
            "Modules": moduleCodeList
        })

    def removeModuleFromUser(self, chatid: int, moduleCode: str):
        """
        Removes module from user. Updates two databases:
        1. module-to-user database
        2. user-to-module database"""

        # Remove the user from the module-to-user list
        self.moduleToUserCollection.document(moduleCode).set({
            "Users": [element for element in self.getUsersFromModule(moduleCode=moduleCode) if element != chatid]
        })

        # Remove the module from the user-to-module list
        self.userToModuleCollection.document(str(chatid)).set({
            "Modules": [module_element for module_element in self.getModulesfromUser(chatid=chatid) if module_element != moduleCode]
        })

    # TODO: Make this module code a *moduleCodes so that I can just call it once instead of looping through.
    def registerUsertoModule(self, chatid: int, moduleCode: str) -> None:
        """
        Updates two databases in firebase:
        1. Updates module-to-user database to register user to module
        2. Updates user-to-module database to allow easy retrieval of list of modules.
        """
        self.addUsertoModule(chatid, moduleCode)
        self.addModuletoUser(chatid, moduleCode)

    def addUsertoModule(self, chatid, moduleCode: str) -> None:
        currentUsersinModule = self.getUsersFromModule(moduleCode)

        # If list is None, make it empty list
        if(currentUsersinModule == None):
            currentUsersinModule = []

        # Check if user is already in user-to-module database, and update database.
        elements_to_remove = []
        for i in range(len(currentUsersinModule)):
            if currentUsersinModule[i] == chatid:
                elements_to_remove.append(i)
        for i in range(len(elements_to_remove)-1, -1, -1):
            currentUsersinModule.pop(i)
        currentUsersinModule.append(chatid)

        self.moduleToUserCollection.document(moduleCode).set({
            "Users": currentUsersinModule
        })

    def addModuletoUser(self, chatid: int, moduleCode: str) -> None:
        currentModulesinUser = self.getModulesfromUser(chatid)

        # If module already in user DB, then skip
        if moduleCode in currentModulesinUser:
            return

        # Check if module is already in user-to-module database, and update database.
        elements_to_remove = []
        for i in range(len(currentModulesinUser)):
            if currentModulesinUser[i] == moduleCode:
                elements_to_remove.append(i)
        for i in range(len(elements_to_remove)-1, -1, -1):
            currentModulesinUser.pop(i)
        currentModulesinUser.append(moduleCode)
        self.userToModuleCollection.document(str(chatid)).set({
            "Modules": currentModulesinUser
        })

    def getUsersFromModule(self, moduleCode: str) -> List[dict]:
        try:
            return self.moduleToUserCollection.document(moduleCode).get().to_dict()["Users"]
        except TypeError:
            return []

    def getModulesfromUser(self, chatid: int) -> List[str]:
        try:
            return self.userToModuleCollection.document(str(chatid)).get().to_dict()["Modules"]
        except TypeError:
            return []

    ########## User-to-User Graph DB ##########
    # This simulates a graph DB for keeping track of which users have convos with which users.
    # Instead of using edge lists, we will use adjacency lists.
    # use self.userToUserCollection.
    # In users, there is a list of dict {userid1: relationship1, userid2: relationship2, ...}

    def registerUserVertice(self, userid: int):
        """Register a user in the User-to-User DB if they aren't already there"""
        if(not str(userid) in self.getAllUserVertices()):
            self.userToUserCollection.document(
                str(userid)).set({"Neighbours": {}})

    def registerUserEdge(self, userid1: int, userid2: int, relationship: str = "Random Matching"):
        """Registers a user1, user2 edge in DB."""
        self.registerUserVertice(userid1)
        self.registerUserVertice(userid2)

        # Add userid2 to userid1.
        user1_neighbours = self.getUserNeighbours(userid1)

        user1_neighbours[str(userid2)] = relationship

        self.userToUserCollection.document(str(userid1)).set(
            {"Neighbours": user1_neighbours})

        # Add userid1 to userid2.
        user2_neighbours = self.getUserNeighbours(userid2)

        user2_neighbours[str(userid1)] = relationship

        self.userToUserCollection.document(str(userid2)).set(
            {"Neighbours": user2_neighbours})

    def deleteUserVertice(self, userid: int):
        for neighbour in self.getUserNeighbours(userid).keys():
            self.deleteUserEdge(userid, neighbour)
        
        self.userToUserCollection.document(str(userid)).delete()

    def deleteUserEdge(self, userid1: int, userid2: int):
        """
        Delets a user1, user2 edge in the DB.
        """
        # Remove userid2 from userid1.
        user1_neighbours = self.getUserNeighbours(userid1)

        if(str(userid2) in user1_neighbours.keys()):
            user1_neighbours.pop(str(userid2))
            self.userToUserCollection.document(str(userid1)).set(
                {"Neighbours": user1_neighbours})

        # Remove userid1 from userid2.
        user2_neighbours = self.getUserNeighbours(userid2)

        if(str(userid1) in user2_neighbours.keys()):
            user2_neighbours.pop(str(userid1))
            self.userToUserCollection.document(str(userid2)).set(
                {"Neighbours": user2_neighbours})

    def printAllUsers(self) -> None:
        """
        Print all users and nodes registered.
        """
        for doc in self.userToUserCollection.get():
            print(f'{doc.id} => {doc.to_dict()}')

    def getAllUserVertices(self) -> List[str]:
        """
        Get all users registered in the User-to-User Graph DB.
        """
        return [doc.id for doc in self.userToUserCollection.get()]

    def getUserNeighbours(self, userid: int) -> Dict[str, str]:
        """
        Get all neighbours (users that this user is currently talking to)
        """
        return self.userToUserCollection.document(str(userid)).get().to_dict()['Neighbours']


fs = FireStoreManager()
fs.printAllUsers()
# print(fs.getAllUserVertices())
fs.registerUserVertice(1234)
fs.registerUserVertice(12345)
fs.registerUserVertice(123456)
fs.registerUserEdge(1234, 12345)
fs.registerUserEdge(12345, 123456)
print(fs.getUserNeighbours(12345))