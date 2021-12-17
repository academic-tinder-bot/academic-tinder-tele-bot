
from __future__ import annotations

import logging
from typing import Dict, List
from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram.ext.jobqueue import JobQueue
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.firebase_handler import GraphHandler
from telegram.ext import *

import re
import json

from random import Random

from database.userdata_handler import registerUser, getUserData


class TeleBot:

    def start(self, update: Update, context: CallbackContext):
        registerUser(name=update.effective_chat.first_name,
                     handle=update.effective_chat.username, chatid=update.effective_chat.id)
        self.firebaseManager.addUser(str(update.effective_chat.id))
        update.message.reply_text(self.main_menu_message())

    ##### Registering module(s) (in convohandler!) #####

    def regModuleStart(self, update: Update, context: CallbackContext):
        self.updateUserModuleDictList(update.effective_chat.id)
        update.message.reply_text(
            self.register_module_message(update.effective_chat.id), reply_markup=self.register_message_keyboard())
        return 0

    def regModuleContinue(self, update: Update, context: CallbackContext):
        message = update.message.text

        # Valid Module Code
        if re.search("[a-zA-Z]{2}[0-9]{4}", update.message.text):
            # Add if there is no duplicate
            if(not update.message.text in self.userModuleDictList[str(update.effective_chat.id)]):
                self.userModuleDictList[str(update.effective_chat.id)].append(
                    (update.message.text.upper()))
            update.message.reply_text(
                self.register_module_message(update.effective_chat.id), reply_markup=self.register_message_keyboard())

        # Invalid Module Code
        else:
            update.message.reply_text("Unknown Module Code!\n" +
                                      self.register_module_message(update.effective_chat.id))

        return 0

    def regModuleExit(self, update: Update, context: CallbackContext):
        query = update.callback_query

        query.message.edit_text(self.register_module_end_message_1())
        modules = self.userModuleDictList[str(update.effective_chat.id)]
        # TODO This is inefficient
        for module in modules:
            self.firebaseManager.addUserModuleEdge(
                userid=str(update.effective_chat.id), moduleCode=module)
        self.userModuleDictList.pop(str(update.effective_chat.id))

        query.answer()
        query.message.edit_text(self.register_module_end_message_2())
        return ConversationHandler.END

    ##### Deleting Modules #####

    def delModuleStart(self, update: Update, context: CallbackContext):
        self.updateUserModuleDictList(update.effective_chat.id)
        update.message.reply_text(self.delete_module_message(
            update.effective_chat.id), reply_markup=self.delete_message_keyboard(update.effective_chat.id))
        return 0

    def delModuleContinue(self, update: Update, context: CallbackContext):
        userid = str(update.effective_chat.id)
        query = update.callback_query
        query.answer()

        if(query.data == "exit_remove_module"):
            query.message.edit_text(self.delete_module_end_message())
            self.firebaseManager.updateUserModules(
                userid=userid, moduleCodes=self.userModuleDictList[userid])
            return ConversationHandler.END
        # Remove module
        moduleRemoved = query.data.removeprefix("module_remove")
        self.userModuleDictList[str(
            update.effective_chat.id)].remove(moduleRemoved)

        query.message.edit_text(self.delete_module_message(
            update.effective_chat.id), reply_markup=self.delete_message_keyboard(update.effective_chat.id))

        return 0

    ##### Chat! #####
    def startChatMenu(self, update: Update, context: CallbackContext):
        # print("startChatMenu")
        update.message.reply_text(self.start_chat_menu_text(
            update.effective_chat.id), reply_markup=self.start_chat_menu_keyboard(update.effective_chat.id))
        return 0

    def currentChatMenu(self, update: Update, context: CallbackContext):
        pass
        return 0

    def beginChatHandler(self, update: Update, context: CallbackContext):
        # print("chatHandler")

        # Starting a new module chat
        callBackData = update.callback_query.data
        print(callBackData)
        if(callBackData.find("start_module_chat") != -1):
            query = update.callback_query
            modulecode = callBackData.removeprefix("start_module_chat_")
            query.message.edit_text("Finding a random user from module {moduleCode}".format(moduleCode = modulecode))
    
            # Get random user
            potentialUsers = self.firebaseManager.getModuleUsers(
                modulecode)
            potentialUsers.remove(str(update.effective_chat.id))
            userMatch = Random().choice(potentialUsers)

            query.message.edit_text("Connecting you with user {}!".format(userMatch))
            self.firebaseManager.addUserUserEdge(userid1=str(update.effective_chat.id), userid2=userMatch, relationship=modulecode)
            # TODO: Try to delay the second message
            # delayed_message = lambda context: query.message.edit_text("Connecting you with user {}!".format(userMatch))    
            # self.updater.job_queue.run_once(delayed_message, 1, context=update.effective_chat.id, name=str(update.effective_chat.id))

            # context.bot.send_message(
            #     chat_id=update.effective_chat.id, text="Connecting you with user {}!".format(userMatch))
            
            self.currentConvos[update.effective_chat.id] = userMatch
            print("TODO: Starting chat in {}".format(modulecode))
            print("User Matched: {}".format(userMatch))

            return 1
        pass

    def exitChatHandler(self, update: Update, context: CallbackContext):
        update.message.reply_text("Exiting Chat!")
        return ConversationHandler.END

    def chatHandler(self, update: Update, context: CallbackContext):
        message = update.message.text
        user = self.currentConvos[update.effective_chat.id]
        update.message.reply_text(
            "Sending message to {user}: {message}".format(user=user, message=message))
        return 1
    ########## MESSAGES ##########

    def main_menu_message(self):
        return "Welcome!"

    def register_module_message(self, chatid):
        modules = self.userModuleDictList[str(chatid)]
        returnString = "Type the module codes here one by one.\nRegistered Modules:\n\n"
        for i in range(len(modules)):
            returnString += "{i}. {moduleCode}\n".format(
                i=i+1, moduleCode=modules[i])
        return returnString

    def register_module_end_message_1(self):
        return "Registering Modules..."

    def register_module_end_message_2(self):
        return "Registered Modules!"

    def delete_module_message(self, chatid):
        modules = self.userModuleDictList[str(chatid)]
        returnString = "Which module to delete? \nRegistered Modules:\n\n"
        for i in range(len(modules)):
            returnString += "{i}. {moduleCode}\n".format(
                i=i+1, moduleCode=modules[i])
        return returnString

    def delete_module_end_message(self):
        return "Deleted Modules!"

    def start_chat_menu_text(self, chatid: int):
        self.updateUserModuleDictList(chatid)
        modules = self.userModuleDictList[str(chatid)]
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

    def delete_message_keyboard(self, chatid):
        modules = self.userModuleDictList[str(chatid)]
        keyboard = [[InlineKeyboardButton(
            moduleCode, callback_data="module_remove"+moduleCode) for moduleCode in modules]]
        keyboard.append([InlineKeyboardButton(
            "exit", callback_data="exit_remove_module")])
        return InlineKeyboardMarkup(keyboard)

    def register_module_keyboard(self):
        keyboard = [[InlineKeyboardButton("exit", callback_data="exit")]]
        return InlineKeyboardMarkup(keyboard)

    def start_chat_menu_keyboard(self, chatid: int):
        modules = self.userModuleDictList[str(chatid)]
        keyboard = [[InlineKeyboardButton(
            moduleCode, callback_data="start_module_chat_"+moduleCode) for moduleCode in modules]]
        keyboard.append([InlineKeyboardButton(
            "exit", callback_data="exit_chat")])
        return InlineKeyboardMarkup(keyboard)
    ##### Util Commands #####

    def updateUserModuleDictList(self, chatid: int):
        self.userModuleDictList[str(chatid)] = self.firebaseManager.getUserModules(
            userid=str(chatid))

    def __init__(self) -> None:

        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        API_KEY = json.load(open("src/keys/telegrambotAPIkey.json"))['API_KEY']
        self.updater = Updater(token=API_KEY)
        self.dispatcher = self.updater.dispatcher

        ########## HANDLERS ##########

        self.dispatcher.add_handler(CommandHandler('start', self.start))

        self.userModuleDictList: Dict[str, List[str]] = {}

        # Register Module
        # TODO: I should actually use a set for this, but whatever
        regModuleConvoHandler = ConversationHandler(
            entry_points=[CommandHandler('regmodule', self.regModuleStart)],
            states={
                0: [MessageHandler(Filters.text, self.regModuleContinue),
                    CallbackQueryHandler(self.regModuleExit, pattern="exit_register_module")]
            },
            fallbacks=[]
        )
        self.dispatcher.add_handler(regModuleConvoHandler)

        # Delete Module
        delModuleConvoHandler = ConversationHandler(
            entry_points=[CommandHandler('delmodule', self.delModuleStart)],
            states={
                0: [CallbackQueryHandler(self.delModuleContinue, pattern="module_remove"),
                    CallbackQueryHandler(self.delModuleContinue, pattern="exit_remove_module")]
            },
            fallbacks=[]
        )
        self.dispatcher.add_handler(delModuleConvoHandler)

        # Handle Chat
        # /startChat --> Select module --> 10 go into chat
        # /currentChat --> Select Chat --> 10 go into chat

        self.currentConvos: Dict[str, str] = {}
        chatConvoHandler = ConversationHandler(
            entry_points=[CommandHandler('startchat', self.startChatMenu),
                          CommandHandler('currentchats', self.currentChatMenu)],
            states={
                0: [CallbackQueryHandler(self.beginChatHandler, pattern='start_module_chat'),
                    CallbackQueryHandler(
                        self.beginChatHandler, pattern='start_chatid'),
                    CallbackQueryHandler(self.exitChatHandler, pattern='exit_chat')],
                1: [CommandHandler('exit', self.exitChatHandler),
                    MessageHandler(Filters.text, self.chatHandler)]
            },
            fallbacks=[]
        )
        self.dispatcher.add_handler(chatConvoHandler)

        self.updater.start_polling()

        self.firebaseManager = GraphHandler()


def main():
    TeleBot()


if __name__ == '__main__':
    main()
