
from __future__ import annotations
from enum import Enum

import logging
from typing import Any, Dict, List
from telegram import Update
import telegram
from telegram.ext import CommandHandler, CallbackQueryHandler, PicklePersistence
from telegram.ext.jobqueue import JobQueue
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.cache.chat_cache_handler import ChatCacheHandler
from database.firebase_handler import GraphHandler
from telegram.ext import *

import re
import json

from random import Random
from datetime import datetime

from database.userdata_handler import registerUser, getUserData
from utils.names import randomAnonName


class UserDataKey(Enum):
    """This is the keys for context.user_data, the dict which stores
    persistent user data across the ConversationHandler.
    --
    USER_MODULES give a list of modules the user is taking (in register/delete module)
    --
    CHAT_ALIAS      --> str (Current alias the user is taking on)
    CURRENT_CHAT_ID --> str (Current chat id that the user is talkign to)
    Gives the following when the user is currently in chat.

    """
    USER_MODULES = 'Modules'     # -> List[str]

    CHAT_ALIAS = 'Alias'         # -> str
    CURRENT_CHAT_ID = 'ID'               # -> str
    CHAT_CACHE = 'Cache'         # -> List[str]
    CHAT_RELATIONSHIP = 'Relationship' # -> str


class BotDataKey(Enum):
    """This is the keys for self.bot_data, the dict which stores
    persistent bot(universal) data. We use self.bot_data instead of self.bot_data because it is more flexible.
    --
    TALKING_TO gives the dict that contains the user (value) in which the user(key) is talking to.
    self.bot_data
     = {
         TALKING_TO: {
             <userid1>: <userthat userid1 is taking to>
        }
    }
    """
    TALKING_TO = "targetuser"


class TeleBot:
    """
    Class that handles all telegram bot implementation.
    Classic case of unnecessary OOP"""

    def start(self, update: Update, context: CallbackContext):
        """Function called with /start. Chat id is logged as an identifier.
        """
        # registerUser(name=update.effective_chat.first_name,
        #              handle=update.effective_chat.username, chatid=update.effective_chat.id)
        self.firebaseManager.addUser(str(update.effective_chat.id))
        update.message.reply_text(self.main_menu_message())

    ##### Registering module(s) (in convohandler!) #####

    def startRegModules(self, update: Update, context: CallbackContext):
        self.updateUserModuleCache(update.effective_chat.id, context.user_data)
        update.message.reply_text(
            self.register_module_message(update.effective_chat.id, context.user_data), reply_markup=self.register_message_keyboard())
        return 0

    def continueRegModules(self, update: Update, context: CallbackContext):
        message = update.message.text

        # Valid Module Code
        if re.search("[a-zA-Z]{2}[0-9]{4}", message):
            # Add if there is no duplicate
            if(not message in context.user_data[UserDataKey.USER_MODULES]):
                context.user_data[UserDataKey.USER_MODULES].append(
                    (message.upper()))
            update.message.reply_text(
                self.register_module_message(update.effective_chat.id, context.user_data), reply_markup=self.register_message_keyboard())

        # Invalid Module Code
        else:
            update.message.reply_text("Unknown Module Code!\n" +
                                      self.register_module_message(update.effective_chat.id, context.user_data))

        return 0

    def exitRegModule(self, update: Update, context: CallbackContext):
        query = update.callback_query

        query.message.edit_text(self.register_module_end_message_1())
        modules = context.user_data[UserDataKey.USER_MODULES]
        # TODO This is inefficient
        for module in modules:
            self.firebaseManager.addUserModuleEdge(
                userid=str(update.effective_chat.id), moduleCode=module)
        context.user_data[UserDataKey.USER_MODULES].pop(
            str(update.effective_chat.id))

        query.answer()
        query.message.edit_text(self.register_module_end_message_2())
        return ConversationHandler.END

    ##### Deleting Modules #####

    def startDelModule(self, update: Update, context: CallbackContext):
        self.updateUserModuleCache(update.effective_chat.id, context.user_data)
        update.message.reply_text(self.delete_module_message(
            update.effective_chat.id, context.user_data), reply_markup=self.delete_message_keyboard(update.effective_chat.id, context.user_data))
        return 0

    def continueDelModule(self, update: Update, context: CallbackContext):
        userid = str(update.effective_chat.id)
        query = update.callback_query
        query.answer()

        if(query.data == "exit_remove_module"):
            query.message.edit_text(self.delete_module_end_message())
            self.firebaseManager.updateUserModules(
                userid=userid, moduleCodes=context.user_data[UserDataKey.USER_MODULES])
            return ConversationHandler.END
        # Remove module
        moduleRemoved = query.data.removeprefix("module_remove")
        context.user_data[UserDataKey.USER_MODULES].remove(moduleRemoved)

        chatid = update.effective_chat.id
        user_data = context.user_data
        query.message.edit_text(self.delete_module_message(
            chatid, user_data), reply_markup=self.delete_message_keyboard(chatid, user_data))

        return 0

    ##### Chat! #####
    def startChatMenu(self, update: Update, context: CallbackContext):
        # print("startChatMenu")
        chatid = update.effective_chat.id
        user_data = context.user_data
        update.message.reply_text(self.start_chat_menu_text(
            chatid, user_data), reply_markup=self.start_chat_menu_keyboard(chatid, user_data))
        return 0

    def currentChatMenu(self, update: Update, context: CallbackContext):

        chatid = update.effective_chat.id
        user_data = context.user_data

        neighbours = self.firebaseManager.getNeighbours(str(chatid))

        resultStr = "Current Chats:\n\n"
        keyboard = []

        unreadMessageCount = self.chatCache.countUnreadMessages(str(chatid))
        # print(unreadMessageCount)
        for i in range(len(neighbours)):
            neighbour = neighbours[i]
            relationship = neighbour[GraphHandler.NEIGHBOUR_RELATIONSHIP_LABEL]
            alias = neighbour[GraphHandler.NEIGHBOUR_ALIAS_LABEL]
            id = neighbour[GraphHandler.NEIGHBOUR_ID_LABEL]

            # Get number of unread Messages
            try: count = unreadMessageCount[id]
            except KeyError: count = 0

            resultStr += f"{relationship}\t{alias}\t{count}"
            keyboard.append([InlineKeyboardButton(
                f"{alias}", callback_data="start_chatid"+id)])

        update.message.reply_text(
            resultStr, reply_markup=InlineKeyboardMarkup(keyboard))
        return 0

    def beginChatHandler(self, update: Update, context: CallbackContext):
        """Handler to begin chat.
        If callbackdata is start_chatid<userid>, then it starts the chat session (continue)
        If callbackdata is start_module_chat_<moduleid>, then it randomly matches the user to start a new chat session.
        """
        # print("chatHandler")

        # Continuing a previous chat
        callBackData = update.callback_query.data
        
        if(callBackData.find("start_chatid") != -1):
            query = update.callback_query
            chatid = callBackData.removeprefix("start_chatid")

            query.message.edit_text(
                f"Connecting you with user {chatid}...")

            edge = self.firebaseManager.getEdge(str(update.effective_chat.id), str(chatid))

            context.user_data[UserDataKey.CURRENT_CHAT_ID] = chatid
            context.user_data[UserDataKey.CHAT_ALIAS] = edge[GraphHandler.NEIGHBOUR_ALIAS_LABEL]
            context.user_data[UserDataKey.CHAT_RELATIONSHIP] = edge[GraphHandler.NEIGHBOUR_RELATIONSHIP_LABEL]
            
            # Update chat log data
            self.bot_data[BotDataKey.TALKING_TO][str(update.effective_chat.id)] = chatid

            query.message.edit_text(
                f"Connected you with user {chatid}!")


            # Send all unread messages
            for message in self.chatCache.popMessagesFromUser(str(update.effective_chat.id), str(chatid)):
                context.bot.send_message(text=message, chat_id = update.effective_chat.id)
            return 1

        # Starting a new module chat
        callBackData = update.callback_query.data
        # print(callBackData)
        chatid = update.effective_chat.id
        if(callBackData.find("start_module_chat") != -1):
            query = update.callback_query
            modulecode = callBackData.removeprefix("start_module_chat_")
            query.message.edit_text(
                "Finding a random user from module {moduleCode}...".format(moduleCode=modulecode))

            # Get random user
            potentialUsers = self.firebaseManager.getModuleUsers(
                modulecode)

            potentialUsers.remove(str(chatid))
            # print(self.firebaseManager.getNeighbours(str(chatid)))
            for user in self.firebaseManager.getNeighbours(str(chatid)):
                if user[self.firebaseManager.NEIGHBOUR_ID_LABEL] in potentialUsers:
                    potentialUsers.remove(
                        user[self.firebaseManager.NEIGHBOUR_ID_LABEL])
            try:
                userMatch = Random().choice(potentialUsers)
            except(IndexError):
                query.message.edit_text(
                    "No valid users to match! Maybe you're currently talking to all of them. Try /currentchats instead!"
                )
                return -1

            alias = randomAnonName()

            query.message.edit_text(
                "Connecting you with user {}!".format(userMatch))
            self.firebaseManager.addUserUserEdge(userid1=str(
                chatid), userid2=userMatch, relationship=modulecode, alias=alias)

            # TODO: Try to delay the second message
            # delayed_message = lambda context: query.message.edit_text("Connecting you with user {}!".format(userMatch))
            # self.updater.job_queue.run_once(delayed_message, 1, context=update.effective_chat.id, name=str(update.effective_chat.id))

            # context.bot.send_message(
            #     chat_id=update.effective_chat.id, text="Connecting you with user {}!".format(userMatch))
            context.user_data[UserDataKey.CURRENT_CHAT_ID] = userMatch
            context.user_data[UserDataKey.CHAT_ALIAS] = alias
            context.user_data[UserDataKey.CHAT_RELATIONSHIP] = modulecode

            # Update chat log data
            self.bot_data[BotDataKey.TALKING_TO][str(update.effective_chat.id)] = userMatch

            query.message.edit_text(
                "Connected you with user {}!".format(userMatch))
            context.bot.send_message(chat_id=userMatch, text="A user connected to you from {}".format(modulecode))
            print("User Matched: {} to {}".format(update.effective_chat.id, userMatch))

            return 1
        pass

    def exitChatHandler(self, update: Update, context: CallbackContext):
        update.message.reply_text("Exiting Chat!")
        self.bot_data[BotDataKey.TALKING_TO].pop(str(update.effective_chat.id))
        return ConversationHandler.END

    def chatHandler(self, update: Update, context: CallbackContext):
        """Handler that handles chat. Is automatically called in ConverstaionHandler.
        """
        # Escape markdown characters
        # TODO: fix this, this just strips characters from any formatting.
        message = self.escapeMarkdown(update.message.text)
        # message = update.message.text
        chatid = str(update.effective_chat.id)
        userid = str(context.user_data[UserDataKey.CURRENT_CHAT_ID])
        alias = context.user_data[UserDataKey.CHAT_ALIAS]
        relationship = context.user_data[UserDataKey.CHAT_RELATIONSHIP]

        time = datetime.now().strftime('%H:%M')

        msg_final = ("`{alias} {time}` \n{message}".format(
            alias=alias, time=time, message=message))
        
        if(self.isInChat(userid, chatid)):
            update.message.reply_text(
                f"Sending message to {userid}: \n\n{msg_final}", parse_mode=telegram.ParseMode.MARKDOWN_V2)
            context.bot.send_message(
                chat_id=userid, text=f"{message}", parse_mode=telegram.ParseMode.MARKDOWN_V2)
        else:
            self.chatCache.addChatMessage(userid, chatid, msg_final)
            update.message.reply_text(
                f"Archiving message to {userid}: \n\n{msg_final}", parse_mode=telegram.ParseMode.MARKDOWN_V2)
            
            context.bot.send_message(
                chat_id=userid, text=f"{alias} from {relationship} just sent you a message\\!\nGo to /currenchats to see their message\\!", parse_mode=telegram.ParseMode.MARKDOWN_V2)

        return 1

    def isInChat(self, user1: str, user2: str) -> bool:
        """Check whether user1 is currently in chat with user2.
        Returns true if user1 is currently in chat with user2.
        """
        try:
            return self.bot_data[BotDataKey.TALKING_TO][user1] == user2
        except (KeyError):
            return False

    def escapeMarkdown(self, text: str) -> str:
        for s in ('_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'):
            text = text.replace(s, '\\{}'.format(s))
        return text
    ########## MESSAGES ##########

    def main_menu_message(self):
        return "Welcome!"

    def register_module_message(self, chatid, user_data):
        modules = user_data[UserDataKey.USER_MODULES]
        returnString = "Type the module codes here one by one.\nRegistered Modules:\n\n"
        for i in range(len(modules)):
            returnString += "{i}. {moduleCode}\n".format(
                i=i+1, moduleCode=modules[i])
        return returnString

    def register_module_end_message_1(self):
        return "Registering Modules..."

    def register_module_end_message_2(self):
        return "Registered Modules!"

    def delete_module_message(self, chatid, user_data):
        modules = user_data[UserDataKey.USER_MODULES]
        returnString = "Which module to delete? \nRegistered Modules:\n\n"
        for i in range(len(modules)):
            returnString += "{i}. {moduleCode}\n".format(
                i=i+1, moduleCode=modules[i])
        return returnString

    def delete_module_end_message(self):
        return "Deleted Modules!"

    def start_chat_menu_text(self, chatid: int, user_data):
        self.updateUserModuleCache(chatid, user_data)
        modules = user_data[UserDataKey.USER_MODULES]
        returnString = "Chat with someone from which module? \nRegistered Modules: \n\n"
        for i in range(len(modules)):
            returnString += "{i}. {moduleCode}\n".format(
                i=i+1, moduleCode=modules[i])
        return returnString

    ########## KEYBOARDS ##########

    def main_menu_keyboard(self):
        keyboard = [[InlineKeyboardButton('Help', callback_data='help')],
                    [InlineKeyboardButton(
                        'Register Module', callback_data='register')],
                    [InlineKeyboardButton(
                        'Chat with someone', callback_data='chat')],
                    [InlineKeyboardButton('See settings', callback_data='settings')]]
        return InlineKeyboardMarkup(keyboard)

    def register_message_keyboard(self):
        keyboard = [[InlineKeyboardButton(
            "exit", callback_data="exit_register_module")]]
        return InlineKeyboardMarkup(keyboard)

    def delete_message_keyboard(self, chatid, user_data):
        modules = user_data[UserDataKey.USER_MODULES]
        keyboard = [[InlineKeyboardButton(
            moduleCode, callback_data="module_remove"+moduleCode) for moduleCode in modules]]
        keyboard.append([InlineKeyboardButton(
            "exit", callback_data="exit_remove_module")])
        return InlineKeyboardMarkup(keyboard)

    def register_module_keyboard(self):
        keyboard = [[InlineKeyboardButton("exit", callback_data="exit")]]
        return InlineKeyboardMarkup(keyboard)

    def start_chat_menu_keyboard(self, chatid: int, user_data):
        modules = user_data[UserDataKey.USER_MODULES]
        keyboard = [[InlineKeyboardButton(
            moduleCode, callback_data="start_module_chat_"+moduleCode) for moduleCode in modules]]
        keyboard.append([InlineKeyboardButton(
            "exit", callback_data="exit_chat")])
        return InlineKeyboardMarkup(keyboard)
    ##### Util Commands #####

    def updateUserModuleCache(self, chatid: int, user_data):
        user_data[UserDataKey.USER_MODULES] = self.firebaseManager.getUserModules(
            userid=str(chatid))

    def __init__(self) -> None:

        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        API_KEY = json.load(open("src/keys/telegrambotAPIkey.json"))['API_KEY']
        # TODO: Persistence
        # persistence = PicklePersistence(filename='conversationbot')
        # self.updater = Updater(token=API_KEY, persistence=persistence)
        self.updater = Updater(token=API_KEY)
        self.dispatcher = self.updater.dispatcher

        ########## HANDLERS ##########

        self.dispatcher.add_handler(CommandHandler('start', self.start))

        # Register Module
        # TODO: I should actually use a set for this, but whatever
        regModuleConvoHandler = ConversationHandler(
            entry_points=[CommandHandler('regmodule', self.startRegModules)],
            states={
                0: [MessageHandler(Filters.text, self.continueRegModules),
                    CallbackQueryHandler(self.exitRegModule, pattern="exit_register_module")]
            },
            fallbacks=[]
        )
        self.dispatcher.add_handler(regModuleConvoHandler)

        # Delete Module
        delModuleConvoHandler = ConversationHandler(
            entry_points=[CommandHandler('delmodule', self.startDelModule)],
            states={
                0: [CallbackQueryHandler(self.continueDelModule, pattern="module_remove"),
                    CallbackQueryHandler(self.continueDelModule, pattern="exit_remove_module")]
            },
            fallbacks=[]
        )
        self.dispatcher.add_handler(delModuleConvoHandler)

        # Handle Chat
        # /startChat --> Select module --> 10 go into chat
        # /currentChat --> Select Chat --> 10 go into chat

        chatConvoHandler = ConversationHandler(
            entry_points=[CommandHandler('startchat', self.startChatMenu),
                          CommandHandler('currentchats', self.currentChatMenu)],
            states={
                0: [CallbackQueryHandler(self.beginChatHandler, pattern='start_module_chat'),
                    CallbackQueryHandler(
                        self.beginChatHandler, pattern='start_chatid'),
                    CallbackQueryHandler(
                        self.exitChatHandler, pattern='exit_chat'),
                    CommandHandler('exit', self.exitChatHandler)],
                1: [CommandHandler('exit', self.exitChatHandler),
                    MessageHandler(Filters.text, self.chatHandler)]
            },
            fallbacks=[]
        )
        self.dispatcher.add_handler(chatConvoHandler)

        self.updater.start_polling()

        self.firebaseManager = GraphHandler()

        self.chatCache = ChatCacheHandler()

        self.bot_data = {}
        self.bot_data[BotDataKey.TALKING_TO] = {}


def main():
    global telebot
    telebot = TeleBot()


def test():

    test = 1
    pass


if __name__ == '__main__':
    main()
    test()
