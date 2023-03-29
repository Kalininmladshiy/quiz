import random
import argparse
import redis

from pathlib import Path
from environs import Env

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler, ConversationHandler
from telegram.ext import Updater
from telegram.ext import MessageHandler, Filters

from quiz_questions import get_questions_answers


QUESTION, SOLUTION = range(2)


def start(update: Update, context: CallbackContext):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет, я бот для викторин!",
        reply_markup=reply_markup,
    )
    return QUESTION


def handle_new_question_request(update: Update, context: CallbackContext, questions_and_answers, redis_connect):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    question = random.choice(list(questions_and_answers))
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=question,
        reply_markup=reply_markup,
    )
    redis_connect.set(update.effective_chat.id, question)
    return SOLUTION


def handle_solution_attempt(update: Update, context: CallbackContext, questions_and_answers, redis_connect):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    if update.message.text.lower() == questions_and_answers[
        redis_connect.get(update.effective_chat.id)
    ]:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Правильно! Для продолжения нажми 'Новый вопрос'",
            reply_markup=reply_markup,
        )
        return QUESTION
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Не правильно!",
            reply_markup=reply_markup,
        )


def surrender(update: Update, context: CallbackContext, questions_and_answers, redis_connect):
    keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    answer = questions_and_answers[redis_connect.get(update.effective_chat.id)]
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
    redis_connect.set(update.effective_chat.id, question)
    return SOLUTION


def main():
    env = Env()
    env.read_env()

    host = env.str('ALLOWED_HOSTS', 'localhost')
    decode_responses = env.bool('DECODE_RESPONSES', True)
    port = env.str('PORT', '6379')
    db = env.str('DB', '0')
    redis_connect = redis.Redis(host=host, port=port, db=db, decode_responses=decode_responses)

    tg_token = env.str('TG_BOT_TOKEN')

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

    questions_and_answers = get_questions_answers(args.path)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTION: [MessageHandler(
                Filters.regex(r'^Новый вопрос$'),
                lambda update, context: handle_new_question_request(update, context, questions_and_answers, redis_connect),
            )],
            SOLUTION: [
                MessageHandler(
                    Filters.regex(r'^Сдаться$'),
                    lambda update, context: surrender(update, context, questions_and_answers, redis_connect),
                ),
                MessageHandler(
                    Filters.text & (~Filters.command),
                    lambda update, context: handle_solution_attempt(update, context, questions_and_answers, redis_connect),
                )
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
