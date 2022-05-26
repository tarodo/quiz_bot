import os

from environs import Env
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from quiz import StateEnum, get_correct_answer, reg_user_question, get_all_questions
from redis_conn import get_redis

PLATFORM_PREFIX = "tg"
QUESTIONS = {}


def keyboard_maker(buttons, number):
    keyboard = [buttons[button: button + number] for button in range(0, len(buttons), number)]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    return markup


def start(update, context):
    buttons = ["Новый вопрос"]
    markup = keyboard_maker(buttons, 2)
    text = "Привет! Я бот для викторин"
    update.message.reply_text(text, reply_markup=markup)
    return StateEnum.FIRST_CHOOSING


def send_new_question(update, context):
    user_id = update.message.from_user.id
    if not QUESTIONS:
        QUESTIONS.update(get_all_questions())
    question_text = reg_user_question(get_redis(), PLATFORM_PREFIX, user_id, QUESTIONS)
    update.message.reply_text(question_text)
    return StateEnum.ATTEMPT


def handle_first_choice(update, context):
    user_message = update.message.text
    if user_message == "Новый вопрос":
        return send_new_question(update, context)


def handle_solution_attempt(update, context):
    attempt = update.message.text
    user_id = update.message.from_user.id
    correct_answer = get_correct_answer(get_redis(), PLATFORM_PREFIX, user_id)
    if attempt.lower() == correct_answer.lower():
        text = "Маладес"
        update.message.reply_text(text)
        return start(update, context)

    buttons = [
        "Сдаться",
    ]
    markup = keyboard_maker(buttons, 2)
    text = "Неправильно… Попробуешь ещё раз?"
    update.message.reply_text(text, reply_markup=markup)
    return StateEnum.ATTEMPT


def handle_giving_up(update, context):
    user_id = update.message.from_user.id
    answer = get_correct_answer(get_redis(), PLATFORM_PREFIX, user_id)
    text = f"Правильный ответ : {answer}"
    update.message.reply_text(text)
    return send_new_question(update, context)


def cancel(update, context):
    user = update.message.from_user
    update.message.reply_text("Всего доброго!", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


if __name__ == "__main__":
    env = Env()
    env.read_env()

    TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(TG_TOKEN)

    dp = updater.dispatcher

    handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            StateEnum.FIRST_CHOOSING: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_first_choice,
                )
            ],
            StateEnum.ATTEMPT: [
                MessageHandler(
                    Filters.text("Сдаться") & ~Filters.command, handle_giving_up
                ),
                MessageHandler(
                    Filters.text & ~Filters.command, handle_solution_attempt
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
    )

    dp.add_handler(handler)

    updater.start_polling()
    updater.idle()
