from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('sqlite:///reminders.db')
Session = sessionmaker(bind=engine)


class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    interval = Column(String, nullable=False)
    reminder_message = Column(String, nullable=False)


Base.metadata.create_all(engine)
