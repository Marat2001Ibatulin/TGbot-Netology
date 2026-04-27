import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import json


Base = declarative_base()

class Word(Base):
    __tablename__ = "word"

    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    russian_word = sq.Column(sq.String(length=40), unique=True)
    target_word = sq.Column(sq.String(length=40))
    wrong_word1 = sq.Column(sq.String(length=40))
    wrong_word2 = sq.Column(sq.String(length=40))
    wrong_word3 = sq.Column(sq.String(length=40))


class User(Base):
    __tablename__ = "user"

    id = sq.Column(sq.BIGINT, primary_key=True)
    first_name = sq.Column(sq.String(length=40))


class UserWord(Base):
    __tablename__ = 'userword'

    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user_id = sq.Column(sq.BIGINT, sq.ForeignKey('user.id'), nullable=False)
    word_id = sq.Column(sq.Integer, sq.ForeignKey('word.id'), nullable=False)

    users = relationship(User, backref='words')
    words = relationship(Word, backref='users')


def create_tables(engine):
    Base.metadata.create_all(engine)

DSN = "postgresql://postgres:{YOURPASSWORD}@localhost:5432/tgbot"
engine = sq.create_engine(DSN)
create_tables(engine)

Session = sessionmaker(bind=engine)
session = Session()

if len(session.query(Word).all()) == 0:
    with open('words.json', encoding='UTF-8') as f:
        dt = json.load(f)

    for i in range(len(dt)):
        word = Word(russian_word=dt[i]['ru'], target_word=dt[i]['correct'], wrong_word1=dt[i]['wrong1'], wrong_word2=dt[i]['wrong2'], wrong_word3=dt[i]['wrong3'])
        session.add(word)

def add_user(chat_id, name, session):
    new_user = User(id=chat_id, first_name=name)
    session.add(new_user)
    q = session.query(Word.id).all()
    for s in q[:30]:
        new_uw = UserWord(user_id=chat_id, word_id=s[0])
        session.add(new_uw)
    session.commit()

session.commit()





