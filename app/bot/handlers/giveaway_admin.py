"""Команды администратора и FSM-диалоги розыгрышей."""
from __future__ import annotations
from datetime import datetime, timedelta
from aiogram import Bot, F, Router, types
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.confirmation import (CANCEL_CALLBACK, CONFIRM_CALLBACK, SKIP_CALLBACK,
    ConfirmationStates, clear_pending_action, confirmation_keyboard, get_pending_action,
    request_confirmation, skip_keyboard)
from app.bot.filters import IsAdminFilter
from app.bot.keyboards import giveaway_keyboard
from app.bot.states import NewGiveawayStates, PickWinnerStates
from app.bot.texts import (giveaway_post_text, participants_list_text, preview_new_giveaway,
    preview_pick_winner, preview_cancel_giveaway, preview_delete_giveaway,
    preview_export_participants, preview_participants_list, report_new_giveaway,
    report_pick_winner, report_cancel_giveaway, report_delete_giveaway,
    report_export_participants, winners_announcement_text)
from app.config import Settings
from app.services.giveaway_service import GiveawayService, GiveawayError, NoParticipantsError

router = Router(name="giveaway_admin")
router.message.filter(IsAdminFilter())

async def _resolve(command: CommandObject, service: GiveawayService, settings: Settings):
    arg=(command.args or "").strip().split()
    if arg and arg[0].isdigit(): return int(arg[0])
    active=await service.get_active_giveaway(settings.channel_id)
    return active.id if active else None

def _positive(text):
    return int(text.strip()) if text and text.strip().isdigit() and int(text.strip()) > 0 else None

async def _preview_new(message, state, settings):
    d=await state.get_data()
    mins=d.get("deadline_minutes")
    await state.set_state(NewGiveawayStates.waiting_confirmation)
    await message.answer(preview_new_giveaway(d["title"], mins, settings.channel_username,
        d.get("description"), bool(d.get("photo_file_id")), d.get("winner_count",1)),
        reply_markup=confirmation_keyboard())

@router.message(Command("newgiveaway"))
async def new_start(message: types.Message, session: AsyncSession, settings: Settings, state: FSMContext):
    active=await GiveawayService(session).get_active_giveaway(settings.channel_id)
    if active:
        await message.answer(f"В канале уже есть активный розыгрыш (id={active.id})."); return
    await state.clear(); await state.set_state(NewGiveawayStates.waiting_title)
    await message.answer("Введите название розыгрыша:")

@router.message(StateFilter(NewGiveawayStates.waiting_title), F.text)
async def new_title(message: types.Message, state: FSMContext):
    title=message.text.strip()
    if not title: await message.answer("Название не может быть пустым."); return
    await state.update_data(title=title); await state.set_state(NewGiveawayStates.waiting_description)
    await message.answer("Введите описание или /skip.")

@router.message(StateFilter(NewGiveawayStates.waiting_description), F.text)
async def new_description(message: types.Message, state: FSMContext):
    value=message.text.strip()
    await state.update_data(description=None if value.lower()=="/skip" else value)
    await state.set_state(NewGiveawayStates.waiting_photo)
    await message.answer("Пришлите одно фото или /skip. Из альбома будет взято первое фото.", reply_markup=skip_keyboard())

@router.message(StateFilter(NewGiveawayStates.waiting_photo), F.photo)
async def new_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(NewGiveawayStates.waiting_winner_count)
    await message.answer("Введите число победителей (целое число больше 0).")

@router.message(StateFilter(NewGiveawayStates.waiting_photo), F.text)
async def new_photo_skip(message: types.Message, state: FSMContext):
    if message.text.strip().lower()!="/skip": await message.answer("Пришлите одно фото или /skip."); return
    await state.update_data(photo_file_id=None); await state.set_state(NewGiveawayStates.waiting_winner_count)
    await message.answer("Введите число победителей (целое число больше 0).")

@router.callback_query(StateFilter(NewGiveawayStates.waiting_photo), F.data==SKIP_CALLBACK)
async def new_photo_skip_button(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(photo_file_id=None); await state.set_state(NewGiveawayStates.waiting_winner_count)
    await callback.message.answer("Введите число победителей (целое число больше 0)."); await callback.answer()

@router.message(StateFilter(NewGiveawayStates.waiting_winner_count), F.text)
async def new_winners(message: types.Message, state: FSMContext):
    n=_positive(message.text)
    if n is None: await message.answer("Введите целое число больше 0."); return
    await state.update_data(winner_count=n); await state.set_state(NewGiveawayStates.waiting_deadline)
    await message.answer("Дедлайн в минутах или /skip для бессрочного розыгрыша.")

@router.message(StateFilter(NewGiveawayStates.waiting_deadline), F.text)
async def new_deadline(message: types.Message, state: FSMContext, settings: Settings):
    t=message.text.strip().lower()
    if t=="/skip": mins=None
    else:
        mins=_positive(t)
        if mins is None: await message.answer("Введите число минут больше 0 или /skip."); return
    await state.update_data(deadline_minutes=mins); await _preview_new(message,state,settings)

@router.callback_query(StateFilter(NewGiveawayStates.waiting_confirmation), F.data==CANCEL_CALLBACK)
async def new_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear(); await callback.message.edit_text("Создание розыгрыша отменено."); await callback.answer()

@router.callback_query(StateFilter(NewGiveawayStates.waiting_confirmation), F.data==CONFIRM_CALLBACK)
async def new_confirm(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, settings: Settings):
    d=await state.get_data(); await state.clear()
    deadline=datetime.utcnow()+timedelta(minutes=d["deadline_minutes"]) if d.get("deadline_minutes") else None
    try:
        service=GiveawayService(session)
        g=await service.create_giveaway(settings.channel_id,d["title"],description=d.get("description"),
            photo_file_id=d.get("photo_file_id"),winner_count=d["winner_count"],deadline=deadline,
            channel_username=settings.channel_username)
        text=giveaway_post_text(g); kb=giveaway_keyboard(g.id)
        if g.photo_file_id:
            sent=await bot.send_photo(chat_id=settings.channel_id,photo=g.photo_file_id,caption=text,reply_markup=kb)
        else:
            sent=await bot.send_message(chat_id=settings.channel_id,text=text,reply_markup=kb)
        await service.register_message(g.id,sent.message_id)
        await callback.message.edit_text(report_new_giveaway(g,settings.channel_username))
    except Exception as e: await callback.message.edit_text(f"Не удалось создать розыгрыш: {e}")
    await callback.answer()

@router.message(Command("pickwinner"))
async def pick_start(message: types.Message, command: CommandObject, session: AsyncSession, settings: Settings, state: FSMContext):
    service=GiveawayService(session); gid=await _resolve(command,service,settings)
    if gid is None: await message.answer("Активный розыгрыш не найден. Укажите ID: /pickwinner <id>"); return
    g=await service.giveaways.get_by_id(gid)
    if not g: await message.answer(f"Розыгрыш {gid} не найден."); return
    count=await service.participants.count_for_giveaway(gid)
    if not count: await message.answer("В розыгрыше нет участников."); return
    raw_args=(command.args or "").strip()
    args=raw_args.split(maxsplit=1)
    custom=args[1] if args and args[0].isdigit() and len(args)>1 else (raw_args if not (args and args[0].isdigit()) else None)
    await state.clear(); await state.update_data(giveaway_id=gid,custom_announcement=custom)
    if custom:
        await _show_pick_preview(message,state,session)
    else:
        await state.set_state(PickWinnerStates.waiting_announcement)
        await message.answer("Введите кастомную фразу завершения или /skip для стандартной.")

async def _show_pick_preview(message,state,session):
    d=await state.get_data(); service=GiveawayService(session); g=await service.giveaways.get_by_id(d["giveaway_id"])
    count=await service.participants.count_for_giveaway(d["giveaway_id"])
    await state.set_state(PickWinnerStates.waiting_confirmation)
    await message.answer(preview_pick_winner(g,count,d.get("custom_announcement")),reply_markup=confirmation_keyboard())

@router.message(StateFilter(PickWinnerStates.waiting_announcement), F.text)
async def pick_announcement(message: types.Message,state: FSMContext,session: AsyncSession):
    value=message.text.strip()
    await state.update_data(custom_announcement=None if value.lower()=="/skip" else value)
    await _show_pick_preview(message,state,session)

@router.callback_query(StateFilter(PickWinnerStates.waiting_confirmation), F.data==CONFIRM_CALLBACK)
async def pick_confirm(callback: types.CallbackQuery,state: FSMContext,session: AsyncSession,bot: Bot,settings: Settings):
    d=await state.get_data(); await state.clear(); service=GiveawayService(session)
    try:
        winners=await service.pick_winners(d["giveaway_id"])
        g=await service.giveaways.get_by_id(d["giveaway_id"])
        await bot.send_message(chat_id=settings.channel_id,text=winners_announcement_text(g,winners,d.get("custom_announcement")))
        await callback.message.edit_text(report_pick_winner(g,winners))
    except GiveawayError as e: await callback.message.edit_text(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(StateFilter(PickWinnerStates.waiting_confirmation), F.data==CANCEL_CALLBACK)
async def pick_cancel(callback: types.CallbackQuery,state: FSMContext):
    await state.clear(); await callback.message.edit_text("Выбор победителя отменён."); await callback.answer()

# Остальные административные команды используют подтверждение.
@router.message(Command("participants"))
async def participants_cmd(message: types.Message,command: CommandObject,session: AsyncSession,settings: Settings,state: FSMContext):
    service=GiveawayService(session); gid=await _resolve(command,service,settings)
    if gid is None: await message.answer("Активный розыгрыш не найден."); return
    g=await service.giveaways.get_by_id(gid); ps=await service.list_participants(gid)
    await request_confirmation(state,"participants",{"giveaway_id":gid})
    await message.answer(preview_participants_list(g,len(ps)),reply_markup=confirmation_keyboard())

@router.message(Command("cancelgiveaway"))
async def cancel_cmd(message: types.Message,command: CommandObject,session: AsyncSession,settings: Settings,state: FSMContext):
    service=GiveawayService(session); gid=await _resolve(command,service,settings); g=await service.giveaways.get_by_id(gid) if gid else None
    if not g: await message.answer("Розыгрыш не найден."); return
    await request_confirmation(state,"cancel",{"giveaway_id":gid}); await message.answer(preview_cancel_giveaway(g),reply_markup=confirmation_keyboard())

@router.message(Command("deletegiveaway"))
async def delete_cmd(message: types.Message,command: CommandObject,session: AsyncSession,state: FSMContext):
    if not command.args or not command.args.strip().isdigit(): await message.answer("Укажите ID: /deletegiveaway <id>"); return
    gid=int(command.args.strip()); service=GiveawayService(session); g=await service.giveaways.get_by_id(gid)
    if not g: await message.answer("Розыгрыш не найден."); return
    n=await service.participants.count_for_giveaway(gid); await request_confirmation(state,"delete",{"giveaway_id":gid})
    await message.answer(preview_delete_giveaway(g,n),reply_markup=confirmation_keyboard())

@router.message(Command("exportparticipants"))
async def export_cmd(message: types.Message,command: CommandObject,session: AsyncSession,settings: Settings,state: FSMContext):
    service=GiveawayService(session); gid=await _resolve(command,service,settings)
    if gid is None: await message.answer("Розыгрыш не найден."); return
    g=await service.giveaways.get_by_id(gid); n=await service.participants.count_for_giveaway(gid)
    await request_confirmation(state,"export",{"giveaway_id":gid}); await message.answer(preview_export_participants(g,n),reply_markup=confirmation_keyboard())

@router.callback_query(StateFilter(ConfirmationStates.waiting_confirmation), F.data==CANCEL_CALLBACK)
async def old_cancel(callback: types.CallbackQuery,state: FSMContext):
    await clear_pending_action(state); await callback.message.edit_text("Действие отменено."); await callback.answer()

@router.callback_query(StateFilter(ConfirmationStates.waiting_confirmation), F.data==CONFIRM_CALLBACK)
async def old_confirm(callback: types.CallbackQuery,state: FSMContext,session: AsyncSession):
    pending=await get_pending_action(state); await clear_pending_action(state)
    if not pending: await callback.answer("Действие уже неактуально.",show_alert=True); return
    action,payload=pending; service=GiveawayService(session); gid=payload["giveaway_id"]
    try:
        if action=="participants":
            g=await service.giveaways.get_by_id(gid); ps=await service.list_participants(gid)
            await callback.message.edit_text(participants_list_text(g.title,ps))
        elif action=="cancel":
            await service.cancel_giveaway(gid); await callback.message.edit_text(report_cancel_giveaway(gid))
        elif action=="delete":
            n=await service.participants.count_for_giveaway(gid); await service.delete_giveaway(gid)
            await callback.message.edit_text(report_delete_giveaway(gid,n))
        elif action=="export":
            csv=await service.export_participants_csv(gid); n=await service.participants.count_for_giveaway(gid)
            await callback.message.answer_document(types.BufferedInputFile(csv.encode(),filename=f"participants_{gid}.csv"),caption=report_export_participants(gid,n))
            await callback.message.delete()
    except GiveawayError as e: await callback.message.edit_text(f"Ошибка: {e}")
    await callback.answer()
