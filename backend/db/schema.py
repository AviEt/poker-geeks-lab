"""
SQLAlchemy ORM models.

Table layout:
  hands       — one row per hand
  players     — one row per player per hand
  streets     — one row per street per hand (preflop/flop/turn/river)
  actions     — one row per action per street
"""

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class HandRow(Base):
    __tablename__ = "hands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(String, nullable=False, unique=True)   # e.g. "RC2031159186"
    game_type = Column(String, nullable=False)
    small_blind = Column(Float, nullable=False)
    big_blind = Column(Float, nullable=False)
    table_name = Column(String, nullable=False)
    played_at = Column(String, nullable=False)              # ISO-8601 string
    hero_name = Column(String, nullable=True)
    pot = Column(Float, nullable=False, default=0.0)
    rake = Column(Float, nullable=False, default=0.0)
    cash_drop = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="USD")
    is_walk = Column(Boolean, nullable=False, default=False)
    allin_equity_json = Column(String, nullable=True)   # JSON: {player_name: equity_fraction}
    allin_pot_bb = Column(Float, nullable=True)         # total pot in BBs at time of all-in
    allin_invested_bb = Column(Float, nullable=True)    # hero's investment in BBs at time of all-in

    players = relationship("PlayerRow", back_populates="hand", cascade="all, delete-orphan")
    streets = relationship("StreetRow", back_populates="hand", cascade="all, delete-orphan",
                           order_by="StreetRow.street_order")


class PlayerRow(Base):
    __tablename__ = "players"
    __table_args__ = (UniqueConstraint("hand_id", "name", name="uq_player_hand_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(Integer, ForeignKey("hands.id"), nullable=False)
    name = Column(String, nullable=False)
    seat = Column(Integer, nullable=False)
    stack = Column(Float, nullable=False)
    position = Column(String, nullable=True)
    hole_cards = Column(String, nullable=True)              # space-separated, e.g. "As Kh"
    net_won = Column(Float, nullable=False, default=0.0)
    pot_won_after_rake = Column(Float, nullable=False, default=0.0)

    hand = relationship("HandRow", back_populates="players")


class StreetRow(Base):
    __tablename__ = "streets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(Integer, ForeignKey("hands.id"), nullable=False)
    name = Column(String, nullable=False)                   # preflop/flop/turn/river
    street_order = Column(Integer, nullable=False)          # 0=preflop, 1=flop, 2=turn, 3=river
    cards = Column(String, nullable=True)                   # space-separated board cards

    hand = relationship("HandRow", back_populates="streets")
    actions = relationship("ActionRow", back_populates="street", cascade="all, delete-orphan",
                           order_by="ActionRow.action_order")


class ActionRow(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    street_id = Column(Integer, ForeignKey("streets.id"), nullable=False)
    action_order = Column(Integer, nullable=False)
    player_name = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    amount = Column(Float, nullable=True)
    is_all_in = Column(Boolean, nullable=False, default=False)

    street = relationship("StreetRow", back_populates="actions")
