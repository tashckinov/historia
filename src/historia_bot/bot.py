from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from historia_bot.ai import AIEngine
from historia_bot.game import DIALOG_PARTNERS, PERIOD_OPTIONS, GameMode, GameState, build_world_update_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_STATES: Dict[int, GameState] = defaultdict(GameState)
WAITING_INPUT: Dict[int, str] = {}
AVAILABLE_MODELS: Dict[int, List[str]] = {}


def mode_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(GameMode.PRESENT.value, callback_data="mode:present")],
        [InlineKeyboardButton(GameMode.PRESENT_WITH_EVENTS.value, callback_data="mode:present_events")],
        [InlineKeyboardButton(GameMode.MODE_2015.value, callback_data="mode:2015")],
    ]
    return InlineKeyboardMarkup(buttons)


def model_keyboard(models: List[str]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(model, callback_data=f"model:{i}")] for i, model in enumerate(models)]
    return InlineKeyboardMarkup(buttons)


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Добавить действие", callback_data="menu:add_action")],
            [InlineKeyboardButton("💬 Диалог", callback_data="menu:dialog")],
            [InlineKeyboardButton("🧠 Советник", callback_data="menu:advisor")],
            [InlineKeyboardButton("⏭ Конец хода", callback_data="menu:end_turn")],
        ]
    )


def dialog_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(partner, callback_data=f"dialog:{partner}")] for partner in DIALOG_PARTNERS]
    return InlineKeyboardMarkup(rows)


def period_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(period, callback_data=f"period:{period}")] for period in PERIOD_OPTIONS]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    USER_STATES[user_id] = GameState()
    WAITING_INPUT.pop(user_id, None)
    AVAILABLE_MODELS.pop(user_id, None)
    await update.message.reply_text(
        "Добро пожаловать в геополитическую AI-игру. Выберите режим:",
        reply_markup=mode_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = USER_STATES[user_id]

    data = query.data
    if data.startswith("mode:"):
        mode_key = data.split(":", 1)[1]
        mapping = {
            "present": GameMode.PRESENT,
            "present_events": GameMode.PRESENT_WITH_EVENTS,
            "2015": GameMode.MODE_2015,
        }
        state.mode = mapping[mode_key]
        try:
            models = AIEngine.list_models()
        except Exception as exc:
            logger.exception("Failed to fetch Ollama models: %s", exc)
            models = []

        if not models:
            await query.message.reply_text(
                "Не удалось получить список моделей из Ollama (http://localhost:11434/api/tags). "
                "Проверьте, что Ollama запущена и модель установлена.")
            return

        AVAILABLE_MODELS[user_id] = models
        await query.message.reply_text("Выберите AI-модель:", reply_markup=model_keyboard(models))
        return

    if data.startswith("model:"):
        models = AVAILABLE_MODELS.get(user_id, [])
        model_index = int(data.split(":", 1)[1])
        if model_index < 0 or model_index >= len(models):
            await query.message.reply_text("Некорректная модель. Выберите заново.")
            return

        state.model = models[model_index]
        WAITING_INPUT[user_id] = "country"
        await query.message.reply_text(f"Выбрана модель: {state.model}\nВведите страну (на русском или английском):")
        return

    if data == "menu:add_action":
        WAITING_INPUT[user_id] = "action"
        await query.message.reply_text("Введите действие вашей страны:")
        return

    if data == "menu:dialog":
        await query.message.reply_text("С кем хотите провести диалог?", reply_markup=dialog_keyboard())
        return

    if data.startswith("dialog:"):
        partner = data.split(":", 1)[1]
        WAITING_INPUT[user_id] = f"dialog:{partner}"
        await query.message.reply_text(f"Введите сообщение для {partner}:")
        return

    if data == "menu:advisor":
        if not state.model:
            await query.message.reply_text("Сначала выберите модель через /start.")
            return
        WAITING_INPUT[user_id] = "advisor"
        await query.message.reply_text("Задайте вопрос советнику:")
        return

    if data == "menu:end_turn":
        if not state.model:
            await query.message.reply_text("Сначала выберите модель через /start.")
            return
        if not state.can_finish_turn():
            await query.message.reply_text("Сначала добавьте хотя бы действие или диалог.")
            return
        await query.message.reply_text("Выберите период перемотки:", reply_markup=period_keyboard())
        return

    if data.startswith("period:"):
        period = data.split(":", 1)[1]
        ai = AIEngine(model=state.model or "qwen3:8b")
        prompt = build_world_update_prompt(state, period)
        try:
            articles = ai.generate_world_update(prompt)
        except Exception as exc:
            logger.exception("AI error: %s", exc)
            await query.message.reply_text("Не удалось получить обновление мира. Проверьте Ollama и попробуйте позже.")
            return

        if not articles:
            await query.message.reply_text("За период не произошло значимых событий.")
        else:
            for i, article in enumerate(articles, 1):
                title = article.get("title", f"Событие {i}")
                description = article.get("description", "")
                await query.message.reply_text(f"📰 {title}\n{description}")

        state.reset_turn()
        await query.message.reply_text("Ход завершён. Следующий ход:", reply_markup=menu_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    state = USER_STATES[user_id]
    text = (update.message.text or "").strip()
    waiting = WAITING_INPUT.get(user_id)

    if waiting == "country":
        state.country = text
        WAITING_INPUT.pop(user_id, None)
        await update.message.reply_text(
            f"Вы играете за: {state.country}. Модель: {state.model}. Выберите действие:",
            reply_markup=menu_keyboard(),
        )
        return

    if waiting == "action":
        ok = state.add_action(text)
        WAITING_INPUT.pop(user_id, None)
        if not ok:
            await update.message.reply_text("Лимит действий за ход достигнут (15).")
        else:
            await update.message.reply_text("Действие добавлено.", reply_markup=menu_keyboard())
        return

    if waiting and waiting.startswith("dialog:"):
        partner = waiting.split(":", 1)[1]
        state.add_dialog(partner, text)
        WAITING_INPUT.pop(user_id, None)
        await update.message.reply_text("Диалог сохранён.", reply_markup=menu_keyboard())
        return

    if waiting == "advisor":
        WAITING_INPUT.pop(user_id, None)
        ai = AIEngine(model=state.model or "qwen3:8b")
        context = (
            f"Режим: {state.mode.value if state.mode else '-'}\n"
            f"Страна: {state.country or '-'}\n"
            f"Модель: {state.model or '-'}\n"
            f"Вопрос игрока: {text}"
        )
        try:
            answer = ai.ask_advisor(context)
        except Exception as exc:
            logger.exception("Advisor error: %s", exc)
            await update.message.reply_text("Советник временно недоступен. Проверьте Ollama.")
            return

        await update.message.reply_text(f"🧠 Советник:\n{answer}", reply_markup=menu_keyboard())
        return

    await update.message.reply_text("Используйте /start для начала новой игры.")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
