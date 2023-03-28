import os
import random
import argparse
import redis

from dotenv import load_dotenv
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler, ConversationHandler
from telegram.ext import Updater
from telegram.ext import MessageHandler, Filters

from quiz_questions import get_questions_answers


REDIS_CONNECT = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
QUESTION = 1


def start(update: Update, context: CallbackContext):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет, я бот для викторин!",
        reply_markup=reply_markup,
    )
    return QUESTION


def handle_new_question_request(update: Update, context: CallbackContext, path):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    questions_and_answers = get_questions_answers(path)
    question = random.choice(list(questions_and_answers))
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=question,
        reply_markup=reply_markup,
    )
    REDIS_CONNECT.set(update.effective_chat.id, question)


def handle_solution_attempt(update: Update, context: CallbackContext, path):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    questions_and_answers = get_questions_answers(path)
    if update.message.text.lower() == questions_and_answers[
        REDIS_CONNECT.get(update.effective_chat.id)
    ]:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Правильно! Для продолжения нажми 'Новый вопрос'",
            reply_markup=reply_markup,
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Не правильно!",
            reply_markup=reply_markup,
        )


def surrender(update: Update, context: CallbackContext, path):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    questions_and_answers = get_questions_answers(path)
    answer = questions_and_answers[REDIS_CONNECT.get(update.effective_chat.id)]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Вот тебе правильный ответ {answer}",
        reply_markup=reply_markup,
    )
    question = random.choice(list(questions_and_answers))
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=question,
        reply_markup=reply_markup,
    )
    REDIS_CONNECT.set(update.effective_chat.id, question)


def main():
    load_dotenv()
    tg_token = os.getenv('TG_BOT_TOKEN')

    updater = Updater(token=tg_token)
    dispatcher = updater.dispatcher

    parser = argparse.ArgumentParser(
        description='Программа загрузки вопросов и ответов из .txt файла'
    )
    parser.add_argument(
        '--path',
        default=Path.cwd() / 'questions_for_quiz',
        help='адрес с .txt файлом',
    )
    args = parser.parse_args()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTION: [MessageHandler(
                Filters.regex(r'^Новый вопрос$'),
                lambda update, context: handle_new_question_request(update, context, args.path),
            ),
                       MessageHandler(
                Filters.regex(r'^Сдаться$'),
                lambda update, context: surrender(update, context, args.path),
            ),
                       MessageHandler(
                Filters.text & (~Filters.command),
                lambda update, context: handle_solution_attempt(update, context, args.path),
            ),
                       ],
        },
        fallbacks=[
            CommandHandler('start', start),
        ]
    )
    dispatcher.add_handler(conv_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
