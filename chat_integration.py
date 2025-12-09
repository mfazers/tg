from aiogram import Router, types
from aiogram.filters import Command
from database import get_employee_by_telegram_id, get_db
from config import ADMIN_IDS, EMPLOYEE_ROLE, ADMIN_ROLE
from keyboards import get_chat_commands_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)

# Dictionary to track chat permissions
chat_permissions = {}

def is_admin(telegram_id):
    """Check if user is an admin"""
    return telegram_id in ADMIN_IDS

def is_authorized_chat(chat_id):
    """Check if the chat is authorized for commands"""
    # For now, allow all chats. In production, check against stored chat IDs
    return True

@router.message(Command("табель"))
async def cmd_timesheet(message: types.Message):
    """Command to submit timesheet - works in both private and group chats"""
    if not is_authorized_chat(message.chat.id):
        await message.answer("❌ Этот чат не авторизован для использования бота.")
        return
    
    # Check if user is registered
    async with get_db() as db:
        employee = get_employee_by_telegram_id(db, message.from_user.id)
        if not employee:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start в личных сообщениях с ботом для регистрации.")
            return
    
    # Send private message to user with timesheet submission instructions
    await message.answer("⏰ Пожалуйста, отправьте фото вашего табеля в личные сообщения боту.")
    
    # Also send to user in private
    try:
        await message.bot.send_message(
            chat_id=message.from_user.id,
            text="📸 Пожалуйста, отправьте фото вашего табеля для подсчета отработанных часов.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ])
        )
    except Exception as e:
        await message.answer("🤖 Пожалуйста, сначала начните общение с ботом в личных сообщениях, чтобы я мог отправлять вам сообщения.")

@router.message(Command("баланс"))
async def cmd_balance(message: types.Message):
    """Command to check balance - works in both private and group chats"""
    if not is_authorized_chat(message.chat.id):
        await message.answer("❌ Этот чат не авторизован для использования бота.")
        return
    
    async with get_db() as db:
        employee = get_employee_by_telegram_id(db, message.from_user.id)
        if not employee:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start в личных сообщениях с ботом для регистрации.")
            return
    
    balance_info = (
        f"💳 Ваш баланс: {employee.balance:.2f} руб.\n"
        f"👤 Имя: {employee.full_name}\n"
        f"💼 Должность: {employee.position or 'Не указана'}\n"
        f"💰 Почасовая ставка: {employee.hourly_rate:.2f} руб./час"
    )
    
    await message.answer(balance_info)

@router.message(Command("сотрудники"))
async def cmd_employees(message: types.Message):
    """Command to view employees - admin only, works in group chats"""
    if not is_authorized_chat(message.chat.id):
        await message.answer("❌ Этот чат не авторизован для использования бота.")
        return
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для просмотра списка сотрудников.")
        return
    
    # This will be implemented in the main bot file
    await message.answer("📋 Список сотрудников будет отображен здесь. Команда доступна в личных сообщениях с ботом.")

@router.message(Command("отчет"))
async def cmd_report(message: types.Message):
    """Command to generate report - admin only"""
    if not is_authorized_chat(message.chat.id):
        await message.answer("❌ Этот чат не авторизован для использования бота.")
        return
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для генерации отчетов.")
        return
    
    await message.answer("📊 Отчет будет сгенерирован. Команда доступна в личных сообщениях с ботом.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Help command for group chat"""
    if not is_authorized_chat(message.chat.id):
        await message.answer("❌ Этот чат не авторизован для использования бота.")
        return
    
    help_text = (
        "🤖 Доступные команды в групповом чате:\n\n"
        "🔸 /табель - отправить табель (работает в личных сообщениях)\n"
        "🔸 /баланс - посмотреть свой баланс\n"
        "🔸 /help - показать эту справку\n\n"
        "Администраторские команды (только для админов):\n"
        "🔸 /сотрудники - просмотреть список сотрудников\n"
        "🔸 /отчет - сгенерировать отчет\n"
    )
    
    await message.answer(help_text)

async def notify_chat_about_timesheet_submission(chat_id, employee_name, hours):
    """Notify the work chat about timesheet submission"""
    try:
        notification_text = f"✅ {employee_name} отправил(а) табель на {hours} часов."
        await bot.send_message(chat_id=chat_id, text=notification_text)
    except Exception as e:
        logger.error(f"Failed to send notification to chat {chat_id}: {e}")

async def notify_chat_about_bonus_penalty(chat_id, employee_name, amount, transaction_type):
    """Notify the work chat about bonus/penalty"""
    try:
        if transaction_type == 'bonus':
            notification_text = f"💰 {employee_name} получил(а) премию: {amount} руб."
        else:
            notification_text = f"❌ {employee_name} получил(а) штраф: {amount} руб."
        
        await bot.send_message(chat_id=chat_id, text=notification_text)
    except Exception as e:
        logger.error(f"Failed to send notification to chat {chat_id}: {e}")

async def notify_chat_about_monthly_reminder(chat_id):
    """Send monthly reminder to submit timesheets"""
    try:
        reminder_text = "📅 Напоминание: Не забудьте отправить табель за прошедший месяц!"
        await bot.send_message(chat_id=chat_id, text=reminder_text)
    except Exception as e:
        logger.error(f"Failed to send reminder to chat {chat_id}: {e}")

# Make bot available globally for notifications
bot = None

def set_bot_instance(bot_instance):
    """Set the bot instance for sending notifications"""
    global bot
    bot = bot_instance