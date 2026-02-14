from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from historia_bot.ai import AIEngine, AIRequestTimeoutError, default_ollama_base_url
from historia_bot.formatting import format_advisor_message
from historia_bot.game import (
    DIALOG_PARTNERS,
    PERIOD_OPTIONS,
    GameMode,
    GameState,
    build_world_update_prompt,
    validate_player_action,
)
from historia_bot.storage import SqliteStorage
from historia_bot.world_state import WorldState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_STATES: Dict[Tuple[int, int], GameState] = {}
WORLD_STATES: Dict[Tuple[int, int], WorldState] = {}
WAITING_INPUT: Dict[Tuple[int, int], str] = {}
AVAILABLE_MODELS: Dict[int, List[str]] = {}
ACTIVE_SESSION: Dict[int, int] = {}
RENAME_TARGET: Dict[int, int] = {}
STORAGE = SqliteStorage(os.environ.get("HISTORIA_DB_PATH", "historia.sqlite3"))


def active_session_id(user_id: int) -> int | None:
    session_id = ACTIVE_SESSION.get(user_id)
    if session_id is not None:
        return session_id
    db_session_id = STORAGE.get_active_session_id(user_id)
    if db_session_id is not None:
        ACTIVE_SESSION[user_id] = db_session_id
    return db_session_id


def set_active_session(user_id: int, session_id: int) -> None:
    ACTIVE_SESSION[user_id] = session_id
    STORAGE.set_active_session(user_id, session_id)


def current_key(user_id: int) -> tuple[int, int] | None:
    session_id = active_session_id(user_id)
    if session_id is None:
        return None
    return (user_id, session_id)


def get_state(user_id: int) -> GameState | None:
    key = current_key(user_id)
    if key is None:
        return None
    if key not in USER_STATES:
        state, waiting, world_state = STORAGE.load_session_state(key[0], key[1])
        USER_STATES[key] = state
        WORLD_STATES[key] = world_state
        if waiting:
            WAITING_INPUT[key] = waiting
    return USER_STATES[key]




def get_world_state(user_id: int) -> WorldState:
    key = current_key(user_id)
    if key is None:
        return WorldState()
    if key not in WORLD_STATES:
        _ = get_state(user_id)
    return WORLD_STATES.get(key, WorldState())

def persist_user(user_id: int) -> None:
    key = current_key(user_id)
    if key is None:
        return
    state = USER_STATES.get(key)
    if state is None:
        return
    STORAGE.save_session_state(key[0], key[1], state, WAITING_INPUT.get(key), WORLD_STATES.get(key, WorldState()))


def set_waiting(user_id: int, waiting: str | None) -> None:
    key = current_key(user_id)
    if key is None:
        return
    if waiting is None:
        WAITING_INPUT.pop(key, None)
    else:
        WAITING_INPUT[key] = waiting
    persist_user(user_id)


def mode_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(GameMode.HISTORICAL_SIMULATION.value, callback_data="mode:historical")],
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


def session_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sessions = STORAGE.list_sessions(user_id)
    rows = [[InlineKeyboardButton("🆕 Начать новую игру", callback_data="session:new")]]
    for session in sessions:
        sid = session["session_id"]
        name = session.get("name") or f"Сессия #{sid}"
        country = session.get("country") or "без страны"
        mode = session.get("mode") or "без режима"
        marker = " (активна)" if session.get("active") else ""
        rows.append(
            [
                InlineKeyboardButton(
                    f"📂 {name}: {country} / {mode}{marker}",
                    callback_data=f"session:open:{sid}",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)




def session_manage_keyboard(session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("▶️ Продолжить", callback_data=f"session:continue:{session_id}")],
            [InlineKeyboardButton("✏️ Переименовать", callback_data=f"session:rename:{session_id}")],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f"session:delete:{session_id}")],
            [InlineKeyboardButton("⬅️ Назад к списку", callback_data="session:back")],
        ]
    )

def quick_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🛑 Завершить сессию")]],
        resize_keyboard=True,
        is_persistent=True,
    )


def menu_message(state: GameState, title: str) -> str:
    if not state.current_turn.actions:
        return f"{title}\n\nВаши действия — это решения вашей страны, не прямое управление чужими странами.\nДействия за ход: пока нет."

    actions = "\n".join(f"{i}. {action.text}" for i, action in enumerate(state.current_turn.actions, 1))
    return f"{title}\n\nВаши действия — это решения вашей страны, не прямое управление чужими странами.\nДействия за ход:\n{actions}"


def dialog_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(partner, callback_data=f"dialog:{partner}")] for partner in DIALOG_PARTNERS]
    return InlineKeyboardMarkup(rows)


def period_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(period, callback_data=f"period:{period}")] for period in PERIOD_OPTIONS]
    return InlineKeyboardMarkup(rows)




async def send_menu_message(message, text: str) -> None:
    await message.reply_text(text, reply_markup=menu_keyboard())
    await message.reply_text("Быстрая кнопка:", reply_markup=quick_actions_keyboard())

async def continue_session_flow(message, user_id: int) -> None:
    state = get_state(user_id)
    if state is None:
        await message.reply_text("Сессия не выбрана.")
        return

    if state.mode and state.model and state.country:
        await send_menu_message(
            message,
            menu_message(
                state,
                f"Продолжаем игру за {state.country} ({state.mode.value}, модель: {state.model}).\nВыберите действие:",
            ),
        )
        return

    if state.mode and not state.model:
        try:
            models = AIEngine.list_models()
        except Exception as exc:
            logger.exception("Failed to fetch Ollama models: %s", exc)
            models = []

        if not models:
            await message.reply_text(
                f"Не удалось получить список моделей из Ollama ({default_ollama_base_url()}/api/tags). "
                "Проверьте, что Ollama запущена и модель установлена."
            )
            return

        AVAILABLE_MODELS[user_id] = models
        await message.reply_text("Выберите AI-модель:", reply_markup=model_keyboard(models))
        return

    if state.mode and state.model and not state.country:
        set_waiting(user_id, "country")
        await message.reply_text("Введите страну (на русском или английском):")
        return

    await message.reply_text("Выберите режим:", reply_markup=mode_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    sessions = STORAGE.list_sessions(user_id)
    if not sessions:
        await update.message.reply_text("У вас пока нет сессий. Начните новую игру:", reply_markup=session_keyboard(user_id))
        return

    await update.message.reply_text(
        "Выберите действие: начать новую игру или открыть существующую сессию.",
        reply_markup=session_keyboard(user_id),
    )


async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    session_id = STORAGE.create_session(user_id, make_active=True)
    set_active_session(user_id, session_id)
    USER_STATES[(user_id, session_id)] = GameState()
    WORLD_STATES[(user_id, session_id)] = WorldState()
    WAITING_INPUT.pop((user_id, session_id), None)
    await update.message.reply_text(f"Новая сессия #{session_id} создана. Выберите режим:", reply_markup=mode_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "session:new":
        session_id = STORAGE.create_session(user_id, make_active=True)
        set_active_session(user_id, session_id)
        USER_STATES[(user_id, session_id)] = GameState()
        WORLD_STATES[(user_id, session_id)] = WorldState()
        WAITING_INPUT.pop((user_id, session_id), None)
        await query.message.reply_text(f"Новая сессия #{session_id} создана. Выберите режим:", reply_markup=mode_keyboard())
        return

    if data.startswith("session:open:"):
        session_id = int(data.split(":", 2)[2])
        await query.message.reply_text(
            f"Сессия #{session_id}. Выберите действие:",
            reply_markup=session_manage_keyboard(session_id),
        )
        return

    if data == "session:back":
        await query.message.reply_text("Выберите сессию:", reply_markup=session_keyboard(user_id))
        return

    if data.startswith("session:continue:"):
        session_id = int(data.split(":", 2)[2])
        set_active_session(user_id, session_id)
        await continue_session_flow(query.message, user_id)
        return

    if data.startswith("session:rename:"):
        session_id = int(data.split(":", 2)[2])
        RENAME_TARGET[user_id] = session_id
        await query.message.reply_text("Введите новое название сессии:")
        return

    if data.startswith("session:delete:"):
        session_id = int(data.split(":", 2)[2])
        STORAGE.delete_session(user_id, session_id)
        ACTIVE_SESSION.pop(user_id, None)
        USER_STATES.pop((user_id, session_id), None)
        WORLD_STATES.pop((user_id, session_id), None)
        WAITING_INPUT.pop((user_id, session_id), None)
        await query.message.reply_text("Сессия удалена.", reply_markup=session_keyboard(user_id))
        return

    state = get_state(user_id)
    if state is None:
        await query.message.reply_text("Сначала выберите или создайте сессию.", reply_markup=session_keyboard(user_id))
        return

    if data.startswith("mode:"):
        mode_key = data.split(":", 1)[1]
        mapping = {
            "historical": GameMode.HISTORICAL_SIMULATION,
        }
        state.mode = mapping[mode_key]
        persist_user(user_id)

        try:
            models = AIEngine.list_models()
        except Exception as exc:
            logger.exception("Failed to fetch Ollama models: %s", exc)
            models = []

        if not models:
            await query.message.reply_text(
                f"Не удалось получить список моделей из Ollama ({default_ollama_base_url()}/api/tags). "
                "Проверьте, что Ollama запущена и модель установлена."
            )
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
        persist_user(user_id)
        set_waiting(user_id, "country")
        await query.message.reply_text(f"Выбрана модель: {state.model}\nВведите страну (на русском или английском):")
        return

    if data == "menu:add_action":
        set_waiting(user_id, "action")
        await query.message.reply_text("Введите действие вашей страны (пример: предложить / начать переговоры / потребовать / поддержать):")
        return

    if data == "menu:dialog":
        await query.message.reply_text("С кем хотите провести диалог?", reply_markup=dialog_keyboard())
        return

    if data.startswith("dialog:"):
        partner = data.split(":", 1)[1]
        set_waiting(user_id, f"dialog:{partner}")
        await query.message.reply_text(f"Введите сообщение для {partner}:")
        return

    if data == "menu:advisor":
        if not state.model:
            await query.message.reply_text("Сначала выберите модель через /start.")
            return
        set_waiting(user_id, "advisor")
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
        world_state = get_world_state(user_id)
        prompt = build_world_update_prompt(state, period, world_state=world_state)

        loading_message = await query.message.reply_text("Генерация мировых событий...")
        try:
            articles = await asyncio.to_thread(ai.generate_world_update, prompt)
        except AIRequestTimeoutError:
            await loading_message.delete()
            await query.message.reply_text(
                "ИИ не успел сгенерировать события за отведённое время. "
                "Попробуйте снова, сократите число действий за ход или увеличьте OLLAMA_REQUEST_TIMEOUT."
            )
            return
        except Exception as exc:
            logger.exception("AI error: %s", exc)
            await loading_message.delete()
            await query.message.reply_text("Не удалось получить обновление мира. Проверьте Ollama и попробуйте позже.")
            return
        await loading_message.delete()

        if not articles:
            await query.message.reply_text("За период не произошло значимых событий.")
        else:
            for i, article in enumerate(articles, 1):
                title = article.get("title", f"Событие {i}")
                description = article.get("description", "")
                await query.message.reply_text(f"📰 {title}\n{description}")

        world_state = get_world_state(user_id)
        world_state.apply_confirmed_updates(articles)

        state.reset_turn()
        persist_user(user_id)
        await send_menu_message(query.message, menu_message(state, "Ход завершён. Следующий ход:"))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if text == "🛑 Завершить сессию":
        key = current_key(user_id)
        if key is None:
            await update.message.reply_text("Активная сессия не выбрана.", reply_markup=session_keyboard(user_id))
            return
        set_waiting(user_id, None)
        STORAGE.clear_active_session(user_id)
        ACTIVE_SESSION.pop(user_id, None)
        await update.message.reply_text(
            "Сессия завершена. Выберите: начать новую игру или продолжить одну из сессий.",
            reply_markup=session_keyboard(user_id),
        )
        return

    rename_session_id = RENAME_TARGET.pop(user_id, None)
    if rename_session_id is not None:
        STORAGE.set_session_name(user_id, rename_session_id, text)
        await update.message.reply_text("Сессия переименована.", reply_markup=session_manage_keyboard(rename_session_id))
        return

    state = get_state(user_id)
    if state is None:
        await update.message.reply_text("Сначала выберите или создайте сессию через /start.")
        return

    key = current_key(user_id)
    waiting = WAITING_INPUT.get(key) if key else None

    if waiting == "country":
        state.country = text
        set_waiting(user_id, None)
        persist_user(user_id)
        await send_menu_message(
            update.message,
            menu_message(state, f"Вы играете за: {state.country}. Модель: {state.model}. Выберите действие:"),
        )
        return

    if waiting == "action":
        validation = validate_player_action(
            player_country=state.country or "",
            action_text=text,
            world_state=get_world_state(user_id),
        )
        set_waiting(user_id, None)

        if not validation.is_valid:
            await update.message.reply_text(
                "Действие отклонено: "
                f"{validation.reason}\n"
                "Попробуйте так:\n"
                "• предложить мирные переговоры по спорному вопросу;\n"
                "• потребовать обсуждение в международном формате (ООН/региональный блок).",
                reply_markup=menu_keyboard(),
            )
            return

        ok = state.add_action(validation.normalized_action)
        persist_user(user_id)
        if not ok:
            await update.message.reply_text("Лимит действий за ход достигнут (15).")
        elif validation.is_partial:
            await send_menu_message(update.message, menu_message(state, f"Действие частично принято: {validation.reason}"))
        else:
            await send_menu_message(update.message, menu_message(state, "Действие добавлено."))
        return

    if waiting and waiting.startswith("dialog:"):
        partner = waiting.split(":", 1)[1]
        state.add_dialog(partner, text)
        set_waiting(user_id, None)
        persist_user(user_id)
        await send_menu_message(update.message, menu_message(state, "Диалог сохранён."))
        return

    if waiting == "advisor":
        set_waiting(user_id, None)
        ai = AIEngine(model=state.model or "qwen3:8b")
        prompt_context = (
            f"Режим: {state.mode.value if state.mode else '-'}\n"
            f"Страна: {state.country or '-'}\n"
            f"Модель: {state.model or '-'}\n"
            f"Вопрос игрока: {text}"
        )
        loading_message = await update.message.reply_text("Генерация ответа советника...")
        try:
            answer = await asyncio.to_thread(ai.ask_advisor, prompt_context)
        except AIRequestTimeoutError:
            await loading_message.delete()
            await update.message.reply_text(
                "Советник не успел ответить за отведённое время. "
                "Попробуйте снова или увеличьте OLLAMA_REQUEST_TIMEOUT."
            )
            return
        except Exception as exc:
            logger.exception("Advisor error: %s", exc)
            await loading_message.delete()
            await update.message.reply_text("Советник временно недоступен. Проверьте Ollama.")
            return
        await loading_message.delete()

        formatted_answer = format_advisor_message(answer)
        await update.message.reply_text(
            f"🧠 Советник:\n{formatted_answer}",
            parse_mode="HTML",
            reply_markup=menu_keyboard(),
        )
        await update.message.reply_text("Быстрая кнопка:", reply_markup=quick_actions_keyboard())
        return

    if state.mode and state.model and state.country:
        await send_menu_message(update.message, menu_message(state, "Продолжаем вашу игру. Выберите действие:"))
        return

    await update.message.reply_text("Используйте /start для выбора или создания сессии.")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newgame", new_game))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt).")


if __name__ == "__main__":
    main()
