import database as db
import sqlalchemy as sq
q = db.session.query(db.Word.russian_word, db.Word.target_word).join(db.UserWord).where(db.UserWord.user_id==1212443541).order_by(sq.func.random()).limit(4).all()
print(q)


