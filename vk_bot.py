import random
import redis
import argparse

import vk_api as vk
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from environs import Env
from pathlib import Path

from quiz_questions import get_questions_answers


def create_keyboard():
    keyboard = VkKeyboard(one_time=False)

    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)

    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def handle_new_question_request(event, vk_api, questions_and_answers, redis_connect):
    question = random.choice(list(questions_and_answers))
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=random.randint(1, 1000),
        keyboard=create_keyboard(),
    )
    redis_connect.set(event.user_id, question)


def handle_solution_attempt(event, vk_api, questions_and_answers, redis_connect):
    if event.text.lower() == questions_and_answers[redis_connect.get(event.user_id)]:
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


def surrender(event, vk_api, questions_and_answers, redis_connect):
    answer = questions_and_answers[redis_connect.get(event.user_id)]
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
    redis_connect.set(event.user_id, question)


def main():
    env = Env()
    env.read_env()
    host = env.str('ALLOWED_HOSTS', 'localhost')
    decode_responses = env.bool('DECODE_RESPONSES', True)
    port = env.str('PORT', '6379')
    db = env.str('DB', '0')
    redis_connect = redis.Redis(host=host, port=port, db=db, decode_responses=decode_responses)

    vk_token = env.str("VK_BOT_TOKEN")
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

    questions_and_answers = get_questions_answers(args.path)

    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == "Сдаться":
                surrender(event, vk_api, questions_and_answers, redis_connect)
            elif event.text == "Новый вопрос":
                handle_new_question_request(event, vk_api, questions_and_answers, redis_connect)
            else:
                handle_solution_attempt(event, vk_api, questions_and_answers, redis_connect)


if __name__ == "__main__":
    main()
