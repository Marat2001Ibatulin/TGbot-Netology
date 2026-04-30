from sqlalchemy import Column, Integer, String, BIGINT, ForeignKey
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

class Word(Base):
    __tablename__ = "word"

    id = Column(Integer, primary_key=True, autoincrement=True)
    russian_word = Column(String(length=40), unique=True)
    target_word = Column(String(length=40))

class User(Base):
    __tablename__ = "user"

    id = Column(BIGINT, primary_key=True)
    first_name = Column(String(length=40))

class UserWord(Base):
    __tablename__ = 'userword'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BIGINT, ForeignKey('user.id'), nullable=False)
    word_id = Column(Integer, ForeignKey('word.id'), nullable=False)

    users = relationship(User, backref='words')
    words = relationship(Word, backref='users')










