
from __future__ import annotations

import logging
from typing import Dict, List
from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.firebase_handler import FireStoreManager as FireBaseManager
from telegram.ext import *

# from utils.user_classes import User
import re
import json

from database.userdata_handler import registerUser, getUserData


class TeleBot:

    def start(self, update: Update, context: CallbackContext):
        registerUser(name=update.effective_chat.first_name, handle=update.effective_chat.username,chatid=update.effective_chat.id)
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
            if(not update.message.text in self.userModuleDictList[update.effective_chat.id]):
                self.userModuleDictList[update.effective_chat.id].append(
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
        modules = self.userModuleDictList[update.effective_chat.id]
        # TODO This is inefficient
        for module in modules:
            self.firebaseManager.registerUsertoModule(
                chatid=update.effective_chat.id, moduleCode=module)
        self.userModuleDictList.pop(update.effective_chat.id)

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
        query = update.callback_query
        query.answer()

        if(query.data == "exit_remove_module"):
            query.message.edit_text(self.delete_module_end_message())
            self.firebaseManager.updateUserModuleList(
                chatid=update.effective_chat.id, moduleCodeList=self.userModuleDictList[update.effective_chat.id])
            return ConversationHandler.END
        # Remove module
        moduleRemoved = query.data.removeprefix("module_remove")
        self.userModuleDictList[update.effective_chat.id].remove(moduleRemoved)

        query.message.edit_text(self.delete_module_message(
            update.effective_chat.id), reply_markup=self.delete_message_keyboard(update.effective_chat.id))

        return 0

    ########## MESSAGES ##########

    def main_menu_message(self):
        return "Welcome!"

    def register_module_message(self, chatid):
        modules = self.userModuleDictList[chatid]
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
        modules = self.userModuleDictList[chatid]
        returnString = "Which module to delete? \nRegistered Modules:\n\n"
        for i in range(len(modules)):
            returnString += "{i}. {moduleCode}\n".format(
                i=i+1, moduleCode=modules[i])
        return returnString

    def delete_module_end_message(self):
        return "Deleted Modules!"

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
        modules = self.userModuleDictList[chatid]
        keyboard = [[InlineKeyboardButton(
            moduleCode, callback_data="module_remove"+moduleCode) for moduleCode in modules]]
        keyboard.append([InlineKeyboardButton(
            "exit", callback_data="exit_remove_module")])
        return InlineKeyboardMarkup(keyboard)

    def register_module_keyboard(self):
        keyboard = [[InlineKeyboardButton("exit", callback_data="exit")]]
        return InlineKeyboardMarkup(keyboard)

    ##### Util Commands #####
    def updateUserModuleDictList(self, chatid: str):
        self.userModuleDictList[chatid] = self.firebaseManager.getModulesfromUser(chatid=chatid)

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


        self.updater.start_polling()

        self.firebaseManager = FireBaseManager.getInstance()


def main():
    TeleBot()


if __name__ == '__main__':
    main()
