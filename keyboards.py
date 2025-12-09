from aiogram import types
from config import ADMIN_ROLE, EMPLOYEE_ROLE

def get_main_menu_keyboard(user_role=EMPLOYEE_ROLE):
    """Main menu keyboard for employees"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📋 Личный кабинет", callback_data="personal_cabinet"),
            types.InlineKeyboardButton(text="📊 История", callback_data="history")
        ],
        [
            types.InlineKeyboardButton(text="⏰ Отправить табель", callback_data="submit_timesheet")
        ]
    ])
    
    # Add admin options if user is admin
    if user_role == ADMIN_ROLE:
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(text="👥 Сотрудники", callback_data="admin_employees"),
            types.InlineKeyboardButton(text="📝 Отчеты", callback_data="admin_reports")
        ])
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(text="💰 Премии/Штрафы", callback_data="admin_transactions")
        ])
    
    return keyboard

def get_personal_cabinet_keyboard():
    """Keyboard for personal cabinet"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="👤 Моя информация", callback_data="my_info"),
        ],
        [
            types.InlineKeyboardButton(text="⏱️ История табелей", callback_data="timesheet_history"),
            types.InlineKeyboardButton(text="💳 История премий/штрафов", callback_data="transaction_history")
        ],
        [
            types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ])
    
    return keyboard

def get_admin_employees_keyboard():
    """Keyboard for admin employees management"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📋 Все сотрудники", callback_data="all_employees"),
        ],
        [
            types.InlineKeyboardButton(text="💰 Настройка ставок", callback_data="set_rates"),
        ],
        [
            types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ])
    
    return keyboard

def get_admin_reports_keyboard():
    """Keyboard for admin reports"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📊 Отчет по зарплатам", callback_data="salary_report"),
            types.InlineKeyboardButton(text="⏱️ Отчет по часам", callback_data="hours_report")
        ],
        [
            types.InlineKeyboardButton(text="💳 Финансовый отчет", callback_data="finance_report"),
        ],
        [
            types.InlineKeyboardButton(text="📥 Экспорт в Excel", callback_data="export_excel"),
        ],
        [
            types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ])
    
    return keyboard

def get_admin_transactions_keyboard():
    """Keyboard for admin transactions (bonuses/penalties)"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="💰 Начислить премию", callback_data="give_bonus"),
            types.InlineKeyboardButton(text="❌ Наложить штраф", callback_data="give_penalty")
        ],
        [
            types.InlineKeyboardButton(text="📋 Подтвердить табели", callback_data="approve_timesheets"),
        ],
        [
            types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ])
    
    return keyboard

def get_history_keyboard():
    """Keyboard for history section"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="⏱️ История табелей", callback_data="timesheet_history"),
            types.InlineKeyboardButton(text="💳 История премий/штрафов", callback_data="transaction_history")
        ],
        [
            types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ])
    
    return keyboard

def get_approve_timesheet_keyboard(time_record_id):
    """Keyboard for approving/rejecting timesheets"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_timesheet_{time_record_id}"),
            types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_timesheet_{time_record_id}")
        ]
    ])
    
    return keyboard

def get_start_keyboard():
    """Keyboard for start command"""
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="/start")],
            [types.KeyboardButton(text="/табель")],
            [types.KeyboardButton(text="/баланс")]
        ],
        resize_keyboard=True
    )
    
    return keyboard

def get_chat_commands_keyboard():
    """Keyboard for chat commands"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📊 Баланс", callback_data="balance"),
            types.InlineKeyboardButton(text="⏱️ Табель", callback_data="submit_timesheet")
        ],
        [
            types.InlineKeyboardButton(text="📋 Сотрудники", callback_data="all_employees")  # Admin only
        ]
    ])
    
    return keyboard