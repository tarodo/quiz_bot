import os
import random

import redis
from environs import Env
from vk_api import VkApi
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkEventType, VkLongPoll

from quiz import StateEnum, get_correct_answer, reg_user_question

PLATFORM_PREFIX = "vk"


def get_user_state(user_id):
    cur_state = redis_db.get(f"{PLATFORM_PREFIX}_{user_id}_state")
    if not cur_state:
        return None
    return int(cur_state)


def set_user_state(user_id, state):
    if state:
        redis_db.set(f"{PLATFORM_PREFIX}_{user_id}_state", str(state))
    else:
        redis_db.delete(f"{PLATFORM_PREFIX}_{user_id}_state")


def keyboard_maker(buttons, number):
    keyboard = VkKeyboard(one_time=True)
    for idx, button in enumerate(buttons):
        keyboard.add_button(button)
        if idx and idx // number == 0:
            keyboard.add_line()
    return keyboard.get_keyboard()


def start(user_id):
    buttons = ["Новый вопрос", "Сдаться", "Мой счёт"]
    text = "Привет! Я бот для викторин"
    vk_api.messages.send(
        user_id=user_id,
        keyboard=keyboard_maker(buttons, 2),
        message=text,
        random_id=random.randint(1, 1000),
    )
    return StateEnum.FIRST_CHOOSING.value


def handle_first_choice(user_id, user_message):
    if user_message == "Новый вопрос":
        return send_new_question(user_id)


def send_new_question(user_id):
    question_text = reg_user_question(redis_db, PLATFORM_PREFIX, user_id)
    vk_api.messages.send(
        user_id=user_id, message=question_text, random_id=random.randint(1, 1000)
    )
    return StateEnum.ATTEMPT.value


def handle_giving_up(user_id):
    answer = get_correct_answer(redis_db, PLATFORM_PREFIX, user_id)
    text = f"Правильный ответ : {answer}"
    vk_api.messages.send(
        user_id=user_id, message=text, random_id=random.randint(1, 1000)
    )
    return send_new_question(user_id)


def handle_solution_attempt(user_id, attempt):
    if attempt == "Сдаться":
        return handle_giving_up(user_id)
    correct_answer = get_correct_answer(redis_db, PLATFORM_PREFIX, user_id)
    if attempt.lower() == correct_answer.lower():
        text = "Маладес"
        vk_api.messages.send(
            user_id=user_id, message=text, random_id=random.randint(1, 1000)
        )
        return send_new_question(user_id)

    buttons = [
        "Сдаться",
    ]
    text = "Неправильно… Попробуешь ещё раз?"
    vk_api.messages.send(
        user_id=user_id,
        keyboard=keyboard_maker(buttons, 1),
        message=text,
        random_id=random.randint(1, 1000),
    )
    return StateEnum.ATTEMPT.value


def quiz(event, vk_api):
    user_id = event.user_id
    user_message = event.message
    user_state = get_user_state(user_id)
    next_state = None
    if not user_state:
        next_state = start(user_id)
    elif user_state == StateEnum.FIRST_CHOOSING.value:
        next_state = handle_first_choice(user_id, user_message)
    elif user_state == StateEnum.ATTEMPT.value:
        next_state = handle_solution_attempt(user_id, user_message)
    set_user_state(user_id, next_state)


if __name__ == "__main__":
    env = Env()
    env.read_env()

    REDIS_URL = env.str("REDIS_URL")
    REDIS_PORT = env.str("REDIS_PORT")
    REDIS_PASS = env.str("REDIS_PASS")
    redis_db = redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=0, password=REDIS_PASS)

    VK_TOKEN = os.getenv("VK_TOKEN")
    vk_session = VkApi(token=VK_TOKEN)
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            quiz(event, vk_api)
