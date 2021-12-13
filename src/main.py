import logging
from telegram import Update
from telegram.ext import callbackcontext, callbackqueryhandler, commandhandler
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import utils.Constants as keys
from telegram.ext import *

import firebase_admin as FirebaseManager


class TeleBot:

    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            self.main_menu_message(), reply_markup=self.main_menu_keyboard())

    def register(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        query.message.edit_text(self.register_message(),
                                reply_markup=self.main_menu_keyboard())

    def chat(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        query.message.edit_text(self.chat_message(),
                                reply_markup=self.main_menu_keyboard())

    def settings(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        query.message.edit_text(self.settings_message(),
                                reply_markup=self.main_menu_keyboard())

    def help(self, update: Update, context: CallbackContext):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=keys.HELP_MESSAGE)

    def getUserInfo(self, update: Update, context: callbackcontext):
        user = update.message.from_user
        context.bot.send_message(chat_id=update.effective_chat.id, text="You are: {}, with username @{}, with chat id {}".format(
            user.name, user.username, update.effective_chat.id))

    ########## KEYBOARDS ##########

    def main_menu_keyboard(self):
        keyboard = [[InlineKeyboardButton('Help', callback_data='help')],
                    [InlineKeyboardButton(
                        'Register Module', callback_data='register')],
                    [InlineKeyboardButton(
                        'Chat with someone', callback_data='chat')],
                    [InlineKeyboardButton('See settings', callback_data='settings')]]

        return InlineKeyboardMarkup(keyboard)

    ########## MESSAGES ##########

    def main_menu_message(self):
        return "What do you want to do?"

    def help_message(self):
        return "TODO"

    def register_message(self):
        return "TODO2"

    def chat_message(self):
        return "TODO3"

    def settings_message(self):
        return "TODO4"

    def __init__(self) -> None:

        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        self.updater = Updater(token=keys.API_KEY)
        self.dispatcher = self.updater.dispatcher

        ########## HANDLERS ##########
        self.dispatcher.add_handler(CommandHandler('start', self.start))
        self.dispatcher.add_handler(CallbackQueryHandler(
            self.register, pattern="register"))
        self.dispatcher.add_handler(
            CallbackQueryHandler(self.chat, pattern="chat"))
        self.dispatcher.add_handler(CallbackQueryHandler(
            self.settings, pattern="settings"))

        self.dispatcher.add_handler(CommandHandler("help", self.help))
        self.dispatcher.add_handler(CommandHandler("whoami", self.getUserInfo))

        self.updater.start_polling()


def main():
    TeleBot()


if __name__ == '__main__':
    main()
