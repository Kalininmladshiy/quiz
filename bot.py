import os
import redis
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler, ConversationHandler
from telegram.ext import Updater
from telegram.ext import MessageHandler, Filters
from main import get_questions_answers, get_random_question


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


def handle_new_question_request(update: Update, context: CallbackContext):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    questions_and_answers = get_questions_answers()
    question = get_random_question(questions_and_answers)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=question,
        reply_markup=reply_markup,
    )
    REDIS_CONNECT.set(update.effective_chat.id, question)


def handle_solution_attempt(update: Update, context: CallbackContext):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    questions_and_answers = get_questions_answers()
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


def surrender(update: Update, context: CallbackContext):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    questions_and_answers = get_questions_answers()
    answer = questions_and_answers[REDIS_CONNECT.get(update.effective_chat.id)]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Вот тебе правильный ответ {answer}",
        reply_markup=reply_markup,
    )
    question = get_random_question(questions_and_answers)
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

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTION: [MessageHandler(Filters.regex(r'^Новый вопрос$'), handle_new_question_request),
                       MessageHandler(Filters.regex(r'^Сдаться$'), surrender),
                       MessageHandler(Filters.text & (~Filters.command), handle_solution_attempt),
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
