import os
import random
from enum import Enum, auto


class StateEnum(Enum):
    FIRST_CHOOSING = auto()
    ATTEMPT = auto()


QUIZ = {}


def get_question(file_name):
    quiz = {}
    with open(file_name, "r", encoding="KOI8-R") as f:
        file_contents = f.read()
    data = file_contents.split("\n\n")
    questions = [
        q[q.find(":") + 2 :].replace("\n", "") for q in data if q.startswith("Вопрос")
    ]
    answers = [q[q.find(":") + 2 :] for q in data if q.startswith("Ответ")]
    if len(questions) == len(answers):
        quiz = dict(zip(questions, answers))
    return quiz


def get_questions_files(dir_name):
    questions_files = [os.path.join(dir_name, f) for f in os.listdir(dir_name)]
    return questions_files


def get_random_question():
    if not QUIZ:
        for quiz_file in get_questions_files("questions/"):
            QUIZ.update(get_question(quiz_file))
    question = random.choice(list(QUIZ.keys()))
    return question, QUIZ[question]


def reg_user_question(redis_db, prefix, user_id):
    question_text, answer_text = get_random_question()
    redis_db.set(f"{prefix}_{user_id}_question", question_text)
    redis_db.set(f"{prefix}_{user_id}_answer", answer_text)
    return question_text


def clear_answer(answer):
    correct_answer = answer[: min(answer.find("."), answer.find("("))]
    return correct_answer.strip()


def get_correct_answer(redis_db, prefix, user_id):
    answer = redis_db.get(f"{prefix}_{user_id}_answer")
    if answer:
        answer = answer.decode("UTF-8")
        return clear_answer(answer)


def main():
    quiz = {}
    for quiz_file in get_questions_files("questions/"):
        quiz.update(get_question(quiz_file))

    print(get_random_question())


if __name__ == "__main__":
    main()
