import random
import os
import redis

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from dotenv import load_dotenv

from main import get_questions_answers, get_random_question

REDIS_CONNECT = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


def create_keyboard():
    keyboard = VkKeyboard(one_time=False)

    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)

    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def handle_new_question_request(event, vk_api):
    questions_and_answers = get_questions_answers()
    question = get_random_question(questions_and_answers)
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=random.randint(1, 1000),
        keyboard=create_keyboard(),
    )
    REDIS_CONNECT.set(event.user_id, question)


def handle_solution_attempt(event, vk_api):
    questions_and_answers = get_questions_answers()
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


def surrender(event, vk_api):
    questions_and_answers = get_questions_answers()
    answer = questions_and_answers[REDIS_CONNECT.get(event.user_id)]
    vk_api.messages.send(
        user_id=event.user_id,
        message=f"Вот тебе правильный ответ {answer}",
        random_id=random.randint(1, 1000),
        keyboard=create_keyboard(),
    )
    question = get_random_question(questions_and_answers)
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

    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == "Сдаться":
                surrender(event, vk_api)
            elif event.text == "Новый вопрос":
                handle_new_question_request(event, vk_api)
            else:
                handle_solution_attempt(event, vk_api)
