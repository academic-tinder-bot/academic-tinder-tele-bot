
from __future__ import annotations

from typing import Dict, List
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate(
    "src/keys/makerthon-2022-9a97e-firebase-adminsdk-qniun-0539fb076e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()  # this connects to our Firestore database


moduleToUserCollection = db.collection(
    'Module-to-User')  # opens 'module-to-user' collection
userToModuleCollection = db.collection("User-to-Module")

userToUserCollection = db.collection("User-to-User")


class _UserModuleGraphHandler():
    """
    Handler for managing two FireStore databases, Module-to-User and User-to-Module DBs.
    Simulates a bipartite graph connecting users to modules with adjacency lists.

    The edges of the graph is labelled with:
    1. Relationship - is the way in which they are matchmaked together (e.g. Module MA1121)
    2. Alias - is what one user is known to the other. To simplify things, both directed edges share the same
    alias. This doesn't compromise anything, so idt it's actually an issue.
    """

    # Label for user adjacency list
    __USER_NEIGHBOUR_LABEL = "Modules"

    # Label for module adjacency list
    __MODULE_NEIGHBOUR_LABEL = "Users"

    def __init__(self) -> None:
        pass

    # add vertice (user)

    def addUser(self, userid: str) -> None:
        """Adds the user in the "user-to-module" database.
        Does nothing if the user already exists."""
        if(not userToModuleCollection.document(userid).get().exists):
            userToModuleCollection.document(
                userid).set({self.__USER_NEIGHBOUR_LABEL: []})

    def removeUser(self, userid: str) -> None:
        """Removes the user from the "user-to-module" database."""
        modules = self.getUserModules(userid)
        for module in modules:
            self.removeUserModuleEdge(userid, module)
        userToModuleCollection.document(userid).delete()

    def addModule(self, moduleCode: str) -> None:
        """Adds a module in the module-to-user database.
        Does nothing if the module already exists."""
        if(not moduleToUserCollection.document(moduleCode).get().exists):
            moduleToUserCollection.document(moduleCode).set(
                {self.__MODULE_NEIGHBOUR_LABEL: []})

    def removeModule(self, moduleCode: str) -> None:
        """Removes a module in the module-to-user database."""
        users = self.getModuleUsers(moduleCode)
        for user in users:
            self.removeUserModuleEdge(user, moduleCode)
        moduleToUserCollection.document(moduleCode).delete()

    def addUsertoModuleDirectedEdge(self, userid: str, moduleCode: str) -> None:
        """Adds a user-module edge in the user-to-module 
        Does nothing if module is already there."""
        modules = self.getUserModules(userid)

        if(not moduleCode in modules):
            modules.append(moduleCode)
            userToModuleCollection.document(
                userid).set({self.__USER_NEIGHBOUR_LABEL: modules})

    def removeUsertoModuleDirectedEdge(self, userid: str, moduleCode: str) -> None:
        """Removes a user-module edge in the user-to-module 
        Does nothing if module is not there."""
        modules = self.getUserModules(userid)

        if(moduleCode in modules):
            modules.remove(moduleCode)
            userToModuleCollection.document(
                userid).set({self.__USER_NEIGHBOUR_LABEL: modules})

    def addModuletoUserDirectedEdge(self, userid: str, moduleCode: str) -> None:
        """Adds a user-module edge in the module-to-user 
        Does nothing if module is not there."""
        users = self.getModuleUsers(moduleCode)

        if(not userid in users):
            users.append(userid)
            moduleToUserCollection.document(
                moduleCode).set({self.__MODULE_NEIGHBOUR_LABEL: users})

    def removeModuletoUserDirectedEdge(self, userid: str, moduleCode: str) -> None:
        """Removes a user-module edge in the module-to-user 
        Does nothing if module is not there."""
        users = self.getModuleUsers(moduleCode)

        if(userid in users):
            users.remove(userid)
            moduleToUserCollection.document(
                moduleCode).set({self.__MODULE_NEIGHBOUR_LABEL: users})

    def addUserModuleEdge(self, userid: str, moduleCode: str) -> None:
        """Adds a user-module edge in both the module-to-user and user-to-module """
        # Just in case
        self.addModule(moduleCode)

        self.addModuletoUserDirectedEdge(userid, moduleCode)
        self.addUsertoModuleDirectedEdge(userid, moduleCode)

    def removeUserModuleEdge(self, userid: str, moduleCode: str) -> None:
        """Removes a user-module edge in both the module-to-user and user-to-module """
        self.removeModuletoUserDirectedEdge(userid, moduleCode)
        self.removeUsertoModuleDirectedEdge(userid, moduleCode)

    def updateUserModules(self, userid: str, moduleCodes: List[str]) -> None:
        """Updates the modules that a user takes to particular list of modules.
        TODO: Place for optimisation here, just directly set the module list instead of updating one-by-one. Use the directed graph edge handlers."""
        currentModules = self.getUserModules(userid)
        for module in moduleCodes:
            if not(module in currentModules):
                self.addUserModuleEdge(userid, module)

        for module in currentModules:
            if not(module in moduleCodes):
                self.removeUserModuleEdge(userid, module)

    # Utils

    def getUserModules(self, userid: str) -> List[str]:
        """Returns a list of the modules the user takes."""
        return userToModuleCollection.document(
            userid).get().to_dict()[self.__USER_NEIGHBOUR_LABEL]

    def getModuleUsers(self, moduleCode: str) -> List[str]:
        """Returns a list of users that is enrolled in the module."""
        return moduleToUserCollection.document(moduleCode).get().to_dict()[self.__MODULE_NEIGHBOUR_LABEL]

    def printUserToModuleDB(self) -> None:
        """Prints all documents in the user-to-module """
        print(
            *[f"\n{document.id} => {document.to_dict()}" for document in userToModuleCollection.get()])

    def printModuletoUserDB(self) -> None:
        """Prints all documents in the module-to-user """
        print(
            *[f"\n{document.id} => {document.to_dict()}" for document in moduleToUserCollection.get()])


class _UserUserGraphHandler():
    """
    Handler for user graphs representing current active chats.
    The dict structure is
    {
        USERID: 
        {   
            name: NAME
            relationship: RELATIONSHIP
            alias: ALIAS
        }
    }
    """
    # Label for list of users
    # For some reason if i dont make this private it goes to the other one instead? TODO Ask stack overflow
    USER_USER_NEIGHBOUR_LABEL = "Neighbours"

    # Labels for each neighbour's id
    NEIGHBOUR_ID_LABEL = "ID"
    # Labels for relationship to neighbour
    NEIGHBOUR_RELATIONSHIP_LABEL = "Relationship"
    # Labels for anonymous alias to neighbour
    NEIGHBOUR_ALIAS_LABEL = "Alias"

    def __init__(self) -> None:
        pass

    def addUser(self, userid: str) -> None:
        """Adds a user to the user-to-user 
        Does nothing if the user already exists."""
        if(not userToUserCollection.document(userid).get().exists):
            userToUserCollection.document(userid).set(
                {self.USER_USER_NEIGHBOUR_LABEL: []})

    def removeUser(self, userid: str) -> None:
        """Deletes a user from the user-to-user 
        TODO: Room for optimisation here, this tries to delete from params(userid) when it will be deleted anyways."""
        userList = self.getNeighbours(userid)
        for user in userList:
            self.removeUsertoUserEdge(userid, user[self.NEIGHBOUR_ID_LABEL])
        userToUserCollection.document(userid).delete()

    def addDirectedUsertoUserEdge(self, userid1: str, userid2: str, relationship: str, alias: str) -> None:
        """Add a directed edge from user1 to user2. More specifically, this
        adds user2 to the adjacency list of user1.
        This needs a relationship and alias label for the edge."""
        user1List = self.getNeighbours(userid1)

        connected = False
        for i in range(len(user1List)):
            if(userid2 == user1List[i][self.NEIGHBOUR_ID_LABEL]):
                connected = True
                break

        if(not connected):
            user1List.append({
                self.NEIGHBOUR_ID_LABEL: userid2,
                self.NEIGHBOUR_RELATIONSHIP_LABEL: relationship,
                self.NEIGHBOUR_ALIAS_LABEL: alias,
            })
            userToUserCollection.document(
                userid1).set({self.USER_USER_NEIGHBOUR_LABEL: user1List})

    def addUserUserEdge(self, userid1: str, userid2: str, relationship: str, alias: str = "No alias") -> None:
        """Adds an user-user edge to the user-to-user DB (updates adjacency lists)
        Does nothing if they are alredy connected.
        This needs a relationship and alias label for the edge.
        """
        self.addDirectedUsertoUserEdge(userid1, userid2, relationship, alias)
        self.addDirectedUsertoUserEdge(userid2, userid1, relationship, alias)

    def removeUsertoUserDirectedEdge(self, userid1: str, userid2: str) -> None:
        """Removes an user-user edge directed the user-to-user DB (updates adjacency list).
        More specifically, it removes user2 from the adjacency list of user1.
        Does nothing if they are not connected.
        """

        neighbourList = self.getNeighbours(userid1)
        for neighbour in neighbourList:
            if(userid2 == neighbour[self.NEIGHBOUR_ID_LABEL]):

                neighbourList.remove(neighbour)
                userToUserCollection.document(
                    userid1).set({self.USER_USER_NEIGHBOUR_LABEL: neighbourList})
                break

    def removeUsertoUserEdge(self, userid1: str, userid2: str) -> None:
        """Removes an user-user edge to the user-to-user DB (updates adjacency lists)
        Does nothing if they are not connected.
        """

        self.removeUsertoUserDirectedEdge(userid1, userid2)
        self.removeUsertoUserDirectedEdge(userid2, userid1)

    # Utils
    def getNeighbours(self, userid: str) -> List[Dict[str, str]]:
        """Get all neighbours of a user in the user-to-user database."""
        # print(userToUserCollection.document(userid).get().to_dict())
        return userToUserCollection.document(userid).get().to_dict()[self.USER_USER_NEIGHBOUR_LABEL]

    def getEdge(self, userid1: str, userid2: str) -> Dict[str, str]: #type: ignore
        """Returns the directed edge from userid1 to userid2.
        More specifically, this returns the edge user1 -> user2, which is stored in the adjacency list of user1."""
        neighbours = self.getNeighbours(userid=userid1)

        for neighbour in neighbours:
            if(neighbour[self.NEIGHBOUR_ID_LABEL] == userid2):
                return neighbour

    def getAllUsers(self) -> List[str]:
        """Get a list of all users in the user-to-user database."""
        return [document.id for document in userToUserCollection.get()]

    def printUsertoUserDB(self) -> None:
        """Prints all documents in the user-to-user """
        print(
            *[f"\n{document.id} => {document.to_dict()}" for document in userToUserCollection.get()])

    def __resetDB(self) -> None:
        """DANGER: Resets ENTIRE firebase user-to-user """
        for user in self.getAllUsers():
            self.removeUser(user)


class GraphHandler(_UserModuleGraphHandler, _UserUserGraphHandler):
    def __init__(self) -> None:
        super().__init__()

    def addUser(self, userid: str):
        _UserModuleGraphHandler().addUser(userid)
        _UserUserGraphHandler().addUser(userid)

    def removeUser(self, userid: str) -> None:
        _UserModuleGraphHandler().removeUser(userid)
        _UserUserGraphHandler().removeUser(userid)


if __name__ == '__main__':
    userGraph = _UserUserGraphHandler()
    userGraph.addUser("1")
    userGraph.addUser("2")
    userGraph.addUserUserEdge("1", "2", "test")
    userGraph.addUserUserEdge("1", "2", "test2")
    pass
