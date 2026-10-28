"""FSM-состояния пошаговых диалогов."""
from aiogram.fsm.state import State, StatesGroup

class NewGiveawayStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_photo = State()
    waiting_winner_count = State()
    waiting_deadline = State()
    waiting_confirmation = State()

class PickWinnerStates(StatesGroup):
    waiting_announcement = State()
    waiting_confirmation = State()
