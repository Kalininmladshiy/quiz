import random
import os
import redis
import argparse

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from dotenv import load_dotenv
from pathlib import Path

from quiz_questions import get_questions_answers

REDIS_CONNECT = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


def create_keyboard():
    keyboard = VkKeyboard(one_time=False)

    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)

    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def handle_new_question_request(event, vk_api, path):
    questions_and_answers = get_questions_answers(path)
    question = random.choice(list(questions_and_answers))
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=random.randint(1, 1000),
        keyboard=create_keyboard(),
    )
    REDIS_CONNECT.set(event.user_id, question)


def handle_solution_attempt(event, vk_api, path):
    questions_and_answers = get_questions_answers(path)
    if event.text.lower() == questions_and_answers[REDIS_CONNECT.get(event.user_id)]:
        vk_api.messages.send(
            user_id=event.user_id,
            message="Правильно! Для продолжения нажми 'Новый вопрос'",
            random_id=random.randint(1, 1000),
            keyboard=create_keyboard(),
        )
    else:
        vk_api.messages.send(
            user_id=event.user_id,
            message="Не правильно!",
            random_id=random.randint(1, 1000),
            keyboard=create_keyboard(),
        )


def surrender(event, vk_api, path):
    questions_and_answers = get_questions_answers(path)
    answer = questions_and_answers[REDIS_CONNECT.get(event.user_id)]
    vk_api.messages.send(
        user_id=event.user_id,
        message=f"Вот тебе правильный ответ {answer}",
        random_id=random.randint(1, 1000),
        keyboard=create_keyboard(),
    )
    question = random.choice(list(questions_and_answers))
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=random.randint(1, 1000),
        keyboard=create_keyboard(),
    )
    REDIS_CONNECT.set(event.user_id, question)


if __name__ == "__main__":
    load_dotenv()
    vk_token = os.getenv("VK_BOT_TOKEN")
    vk_session = vk.VkApi(token=vk_token)
    vk_api = vk_session.get_api()

    parser = argparse.ArgumentParser(
        description='Программа загрузки вопросов и ответов из .txt файла'
    )
    parser.add_argument(
        '--path',
        default=Path.cwd() / 'questions_for_quiz',
        help='адрес с .txt файлом',
    )
    args = parser.parse_args()

    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == "Сдаться":
                surrender(event, vk_api, args.path)
            elif event.text == "Новый вопрос":
                handle_new_question_request(event, vk_api, args.path)
            else:
                handle_solution_attempt(event, vk_api, args.path)
