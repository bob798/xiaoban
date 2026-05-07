import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, func
from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, nullable=False, index=True)
    occupation = Column(String, default="")
    english_level = Column(String, default="B1")
    learning_goal = Column(String, default="")
    raw_json = Column(Text, default="{}")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserFact(Base):
    __tablename__ = "user_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())


class GrammarCard(Base):
    __tablename__ = "grammar_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False)          # e.g. "go/went past tense"
    description = Column(Text, default="")
    # FSRS fields
    due = Column(DateTime, default=func.now())
    stability = Column(Float, default=0.0)
    difficulty = Column(Float, default=0.0)
    reps = Column(Integer, default=0)
    lapses = Column(Integer, default=0)
    state = Column(Integer, default=0)            # 0=New, 1=Learning, 2=Review, 3=Relearning
    last_review = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)        # user / assistant / system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
