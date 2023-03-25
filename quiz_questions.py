import os
import random
import re


def get_random_question(questions_and_answers):
    random_question = random.choice(list(questions_and_answers))
    return random_question


def get_files_names(path):
    files_names = []
    for root, dirs, files in os.walk(path):
        for filename in files:
            files_names.append(filename)
    return files_names


def get_questions_answers(path_to_files):
    remove_chars = {ord(','): None, ord(':'): None, ord('.'): None, ord('"'): None}
    files_names = get_files_names(path_to_files)
    questions = []
    answers = []
    for file_name in files_names:
        with open(os.path.join(path_to_files, file_name), "r", encoding="KOI8-R") as my_file:
            file_contents = my_file.read().split('\n\n')
        for string in file_contents:
            if 'Вопрос' in string:
                questions.append(' '.join(string.splitlines()))
            if 'Ответ:' in string:
                answer = ' '.join(string.splitlines())[6:].lower().translate(remove_chars).strip()
                answers.append(re.sub(r'\[.*\]', '', answer))

    questions_and_answers = dict(zip(questions, answers))
    return questions_and_answers
