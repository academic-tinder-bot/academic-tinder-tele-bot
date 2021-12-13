from threading import current_thread
import firebase_admin
from firebase_admin import credentials, firestore

from utils.user_classes import User


class FireStoreManager:

    def __init__(self) -> None:
        self.cred = credentials.Certificate(
            "src\serviceacckey\makerthon-2022-9a97e-firebase-adminsdk-qniun-0539fb076e.json")
        firebase_admin.initialize_app(self.cred)

        self.db = firestore.client()  # this connects to our Firestore database
        self.moduleToUserCollection = self.db.collection(
            'Module-to-User')  # opens 'module-to-user' collection
        self.userToModuleCollection = self.db.collection("User-to-Module")

    def unregisterUser(self, user: User):
        """
        Removes user from both module-to-user and user-to-module databases. Removes user purely by chatid, nothing else.
        """
        for module in self.getModulesfromUser(user):
            self.removeUserFromModule(user, module)
        # Firebase can't delete stuff, so this will do for now
        self.userToModuleCollection.document(user.chatid).set(None)
        self.userToModuleCollection.document(user.chatid).delete()

    def removeUserFromModule(self, user:User, moduleCode:str):
        """
        Removes a user a specific module. Updates both databases.
        """
        modules_now = self.getUsersFromModule(moduleCode)
        modules_now.remove(user.toDict())
        self.moduleToUserCollection.document(moduleCode).set({
            "Users": modules_now
        })
    def unregisterModule(self, modulecode: str):
        """
        TODO: Removes module from both module-to-user and user-to-module databases. Removes user purely by module code.
        """

    def registerUsertoModule(self, user: User, moduleCode: str) -> None:
        """
        Updates two databases in firebase:
        1. Updates module-to-user database to register user to module
        2. Updates user-to-module database to allow easy retrieval of list of modules.
        """
        self.addUsertoModule(user, moduleCode)
        self.addModuletoUser(user, moduleCode)

    def addUsertoModule(self, user: User, moduleCode: str) -> None:
        currentUsersinModule = self.getUsersFromModule(moduleCode)

        # If list is None, make it empty list
        if(currentUsersinModule == None): currentUsersinModule = []

        # Check if user is already in user-to-module database, and update database.
        elements_to_remove = []
        for i in range(len(currentUsersinModule)):
            if User.fromDict(currentUsersinModule[i]) == user:
                elements_to_remove.append(i)
        for i in range(len(elements_to_remove)-1, -1, -1):
            currentUsersinModule.pop(i)
        currentUsersinModule.append(user.toDict())

        self.moduleToUserCollection.document(moduleCode).set({
            "Users": currentUsersinModule
        })

    def addModuletoUser(self, user: User, moduleCode: str) -> None:
        currentModulesinUser = self.getModulesfromUser(user)

        # If list is None, make it empty list
        if(currentModulesinUser == None): currentModulesinUser = []

        # Check if user is already in module-to-user database, and update database.
        elements_to_remove = []
        for i in range(len(currentModulesinUser)):
            if currentModulesinUser[i] == moduleCode:
                elements_to_remove.append(i)
        for i in range(len(elements_to_remove)-1, -1, -1):
            currentModulesinUser.pop(i)
        currentModulesinUser.append(moduleCode)

        self.userToModuleCollection.document(user.chatid).set({
            "Modules": currentModulesinUser
        })

    def getUsersFromModule(self, moduleCode: str) -> list[dict]:
        try:
            return self.moduleToUserCollection.document(moduleCode).get().to_dict()["Users"]
        except TypeError:
            return []

    def getModulesfromUser(self, user: User) -> list[str]:
        try:
            return self.userToModuleCollection.document(user.chatid).get().to_dict()["Modules"]
        except TypeError:
            return []



fs = FireStoreManager()
fs.registerUsertoModule(User("1", "5", "3"), "MA1521")
fs.registerUsertoModule(User("1", "5", "3"), "MA1522")
fs.registerUsertoModule(User("1", "5", "3"), "MA1523")
fs.registerUsertoModule(User("1", "2", "4"), "MA1521")
fs.registerUsertoModule(User("1", "2", "4"), "MA1523")
fs.registerUsertoModule(User("1", "2", "4"), "MA1524")
# fs.unregisterUser(User("1","2","4"))
