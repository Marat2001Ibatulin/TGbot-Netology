import random
from langdetect import detect
from telebot.types import  ReplyKeyboardRemove
import database as db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from deep_translator import GoogleTranslator
import requests
import json

#https://web.telegram.org/a/#8694713273 - ссылка на бота

DSN = {DNS}
engine = create_engine(DSN)
Session = sessionmaker(bind=engine)
session = Session()

def create_tables():
    db.Base.metadata.create_all(engine)
    basic_words()

def basic_words():
    if len(session.query(db.Word).all()) == 0:
        with open('words.json', encoding='UTF-8') as f:
            dt = json.load(f)

        for i in range(len(dt)):
            word = db.Word(russian_word=dt[i]['ru'], target_word=dt[i]['correct'])
            session.add(word)

create_tables()

def add_user(chat_id, name):
    new_user = db.User(id=chat_id, first_name=name)
    session.add(new_user)
    q = session.query(db.Word.id).order_by(db.Word.id).limit(30).all() # добавляются только 30 первых общих слов, а не все слова в базе
    for s in q:
        new_uw = db.UserWord(user_id=chat_id, word_id=s[0])
        session.add(new_uw)
    session.commit()

state_storage = StateMemoryStorage()
TOKEN = {TOKEN}
bot = TeleBot(TOKEN, state_storage=state_storage)

def show_hint(*lines):
    return '\n'.join(lines)

def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"

class Command:
    ADD_WORD = 'Добавить слово ✏️'
    DELETE_WORD = 'Удалить слово 👉🏻🗑️'
    NEXT = 'Дальше ⏩'
    CANCEL = 'Отмена ❎'
    Yes = 'Да ✅'

class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет. \U0001F600 Я SimpleBot. Давай изучать английские слова! Используй команду /cards для генерации слов и вариантов перевода.")
    cid = message.chat.id
    q = session.query(db.User.id).all()
    for i in q:
        if id in i:
            break
    else:
        add_user(chat_id=cid, name=message.from_user.first_name)

@bot.message_handler(commands=['cards'])
def create_cards(message):
    cid = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2)
    q = (
        session
        .query(db.Word.russian_word, db.Word.target_word)
        .join(db.UserWord).where(db.UserWord.user_id==cid)
        .order_by(func.random())
        .limit(4)
        .all()
                        )
    word_pair = q.pop()
    target_word = word_pair[1]
    translate =  word_pair[0]
    buttons = []
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = [word[1] for word in q]
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)
    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    count = word_count(message)
    if count > 4:
        bot.send_message(message.chat.id,'Слово больше не будет показываться для Вас.', reply_markup=ReplyKeyboardRemove())
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            buttons =[]
            markup = types.InlineKeyboardMarkup(row_width=2)
            yes_btn = types.InlineKeyboardButton(Command.Yes, callback_data='delete_approval')
            buttons.append(yes_btn)
            no_btn = types.InlineKeyboardButton(Command.CANCEL, callback_data='delete_cancellation')
            buttons.append(no_btn)
            markup.add(*buttons)
            bot.send_message(message.chat.id, f'Вы уверены, что хотите удалить {data['translate_word']}', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f'Вы не можете изучать менее 4 слов') # Кол-во изучаемых слов всегда достаточно для генерации карты

@bot.callback_query_handler(func=lambda call: call.data == "delete_cancellation")
def delete_no(call):
    buttons =[]
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    bot.send_message(call.from_user.id, 'Удаление отменено', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "delete_approval")
def delete_yes(call):
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        print(f'{data['translate_word']} удаляется для пользователя с chat id {call.message.chat.id}')
        word_id = session.query(db.Word.id).filter(db.Word.russian_word==data['translate_word']).scalar()
        session.query(db.UserWord).filter(db.UserWord.user_id==call.from_user.id, db.UserWord.word_id==word_id).delete()
        session.commit()
        buttons = []
        next_btn = types.KeyboardButton(Command.NEXT)
        add_word_btn = types.KeyboardButton(Command.ADD_WORD)
        buttons.extend([next_btn, add_word_btn])
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*buttons)
        bot.send_message(call.message.chat.id, 'Слово удалено', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    buttons = []
    rand_btn = types.KeyboardButton('Случайное слово')
    inpt_btn = types.KeyboardButton('Ввести слово')
    back_btn = types.KeyboardButton('Вернуться к угадыванию')
    buttons.extend([rand_btn, inpt_btn, back_btn])
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(*buttons)
    bot.send_message(cid, 'Желаете ввести слово или добавить случайное?', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Вернуться к угадыванию')
def stop_adding(message):
    buttons =[]
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    buttons.extend([next_btn, add_word_btn])
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    bot.send_message(message.chat.id, 'Отмена добавления', reply_markup=markup)

def add_completed(message):
    buttons =[]
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    buttons.extend([next_btn, add_word_btn])
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    bot.send_message(message.chat.id, 'Слово добавлено', reply_markup=markup)

@bot.message_handler(commands=['help'])
def show_info(message):
    bot.send_message(message.chat.id, 'Боту известны следующие команды:\n'
                                      '/start - для начала\n'
                                      '/help - для информации\n'
                                      '/count - количество изучаемых слов\n'
                                      '/cards - начать угадывать слова')

@bot.message_handler(commands=['count'])
def word_count(message):
    counter = len(session.query(db.UserWord).filter(db.UserWord.user_id==message.chat.id).all())
    bot.send_message(message.chat.id, f'Количество изучаемых слов: {counter}')
    return counter

@bot.message_handler(func=lambda message: message.text == 'Случайное слово')
def add_random_word(message):
    url = "https://random-word-api.herokuapp.com/word"
    response = requests.get(url)
    if response.status_code == 200:
        eng_word = response.json()[0]
        msg = bot.send_message(message.from_user.id, f'Добавляется слово {eng_word}')
        process_word(msg)
    else:
        bot.send_message(message.from_user.iв, 'Ошибка. Попробуйте позднее')
        stop_adding(message)

@bot.message_handler(func=lambda message: message.text == 'Ввести слово')
def add_input_word(message):
    cid = message.chat.id
    msg = bot.send_message(cid, 'Введите слово', reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_word)

def process_word(word):
    cid = word.chat.id
    word_str = word.text.strip().lower()
    if len(word_str.split()) > 1:
        word_str = word_str.split()[2]
    if word_str.isalpha():
        if detect(word_str) == 'ru':
            russian_word = word_str
        else:
            russian_word = GoogleTranslator(source='en', target='ru').translate(word_str)
        count = (
        session.query(db.Word.russian_word)
        .filter(db.Word.russian_word==russian_word)
        .count()
         )
        if count:
            count2= (
                session.
                query(db.UserWord).
                join(db.Word).
                filter(db.Word.russian_word==russian_word, db.UserWord.user_id==cid).
                count()
             )
            if count2:
                bot.send_message(word.from_user.id, 'Вы уже учите данное слово')
                stop_adding(word)
            else:
                w_id = session.query(db.Word.id).filter(db.Word.russian_word==russian_word).scalar()
                new_link = db.UserWord(user_id=cid, word_id=w_id)
                session.add(new_link)
                session.commit()
                add_completed(word)
        else:
            translate_word = GoogleTranslator(source='ru', target='en').translate(russian_word)
            added_word = db.Word(
                russian_word=russian_word,
                target_word=translate_word,
            )
            session.add(added_word)
            session.commit()
            w_id = session.query(db.Word.id).filter(db.Word.russian_word==russian_word).scalar()
            new_link = db.UserWord(user_id=cid, word_id=w_id)
            session.add(new_link)
            session.commit()
            add_completed(word)
    else:
        bot.send_message(word.from_user.id, 'Допустимы только буквы')
        stop_adding(word)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            buttons = []
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            buttons = [types.KeyboardButton(btn) for btn in data['other_words']]
            for btn in buttons:
                if btn.text == text:
                    if '❌' not in btn.text:
                        btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
            buttons.append(types.KeyboardButton(target_word))
            random.shuffle(buttons)
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
        markup.add(*buttons)
        bot.send_message(message.chat.id, hint, reply_markup=markup)

bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling()