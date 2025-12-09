import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.enums.content_type import ContentType
from database import init_db, get_employee_by_telegram_id, create_employee, get_db, add_time_record, add_transaction, update_employee_rate, get_employee_history
from config import BOT_TOKEN, ADMIN_IDS
from keyboards import get_main_menu_keyboard, get_personal_cabinet_keyboard, get_admin_employees_keyboard, get_admin_reports_keyboard, get_admin_transactions_keyboard, get_history_keyboard, get_approve_timesheet_keyboard
from ocr_processor import process_timesheet_image
from chat_integration import router as chat_router, set_bot_instance
from export_manager import export_manager
from scheduler import scheduler
import tempfile
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Set bot instance for chat integration
set_bot_instance(bot)

# FSM States for user interactions
class RegistrationState(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_position = State()

class AdminState(StatesGroup):
    waiting_for_employee_selection = State()
    waiting_for_bonus_amount = State()
    waiting_for_penalty_amount = State()
    waiting_for_new_rate = State()

class TimesheetState(StatesGroup):
    waiting_for_timesheet_photo = State()

# Register chat commands router
dp.include_router(chat_router)

# Start command handler
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command and register new employees"""
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    
    async with get_db() as db:
        employee = get_employee_by_telegram_id(db, telegram_id)
        
        if not employee:
            # New employee registration
            await message.answer(
                f"Привет, {full_name}! Вы не зарегистрированы в системе.\n"
                f"Пожалуйста, укажите ваше ФИО для завершения регистрации:"
            )
            await state.set_state(RegistrationState.waiting_for_full_name)
        else:
            # Existing employee
            role = employee.role
            await message.answer(
                f"Добро пожаловать, {employee.full_name}!\n"
                f"Ваша должность: {employee.position or 'Не указана'}\n"
                f"Баланс: {employee.balance:.2f} руб.",
                reply_markup=get_main_menu_keyboard(role)
            )

@dp.message(RegistrationState.waiting_for_full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Process full name during registration"""
    full_name = message.text.strip()
    
    if len(full_name.split()) < 2:
        await message.answer("Пожалуйста, укажите полное ФИО (минимум имя и фамилия):")
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationState.waiting_for_position)
    await message.answer("Теперь укажите вашу должность:")

@dp.message(RegistrationState.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    """Process position during registration"""
    data = await state.get_data()
    full_name = data.get('full_name')
    position = message.text.strip()
    
    async with get_db() as db:
        # Determine role based on admin IDs
        role = 'admin' if message.from_user.id in ADMIN_IDS else 'employee'
        
        employee = create_employee(db, message.from_user.id, full_name, position)
        employee.role = role
        db.commit()
        
        await message.answer(
            f"✅ Регистрация завершена!\n"
            f"ФИО: {employee.full_name}\n"
            f"Должность: {employee.position}\n"
            f"Роль: {employee.role}\n\n"
            f"Добро пожаловать в систему учета рабочего времени!",
            reply_markup=get_main_menu_keyboard(employee.role)
        )
    
    await state.clear()

# Main menu callback handlers
@dp.callback_query(F.data == "main_menu")
async def show_main_menu(call: CallbackQuery):
    """Show main menu"""
    async with get_db() as db:
        employee = get_employee_by_telegram_id(db, call.from_user.id)
        if employee:
            await call.message.edit_text(
                f"Главное меню\nДобро пожаловать, {employee.full_name}!",
                reply_markup=get_main_menu_keyboard(employee.role)
            )
    await call.answer()

@dp.callback_query(F.data == "personal_cabinet")
async def show_personal_cabinet(call: CallbackQuery):
    """Show personal cabinet"""
    await call.message.edit_text("Личный кабинет", reply_markup=get_personal_cabinet_keyboard())
    await call.answer()

@dp.callback_query(F.data == "my_info")
async def show_my_info(call: CallbackQuery):
    """Show employee's personal information"""
    async with get_db() as db:
        employee = get_employee_by_telegram_id(db, call.from_user.id)
        if employee:
            info_text = (
                f"👤 Моя информация:\n\n"
                f"ФИО: {employee.full_name}\n"
                f"Должность: {employee.position or 'Не указана'}\n"
                f"Почасовая ставка: {employee.hourly_rate:.2f} руб./час\n"
                f"Баланс: {employee.balance:.2f} руб.\n"
                f"Роль: {employee.role}\n"
                f"Дата регистрации: {employee.created_at.strftime('%d.%m.%Y %H:%M') if employee.created_at else 'N/A'}"
            )
            await call.message.edit_text(info_text, reply_markup=get_personal_cabinet_keyboard())
    await call.answer()

@dp.callback_query(F.data == "history")
async def show_history(call: CallbackQuery):
    """Show history menu"""
    await call.message.edit_text("История", reply_markup=get_history_keyboard())
    await call.answer()

@dp.callback_query(F.data == "timesheet_history")
async def show_timesheet_history(call: CallbackQuery):
    """Show timesheet history"""
    async with get_db() as db:
        employee = get_employee_by_telegram_id(db, call.from_user.id)
        if employee:
            time_records, transactions = get_employee_history(db, employee.id)
            
            if not time_records:
                history_text = "⏰ История табелей пуста"
            else:
                history_text = "⏰ История табелей:\n\n"
                for record in time_records[-10:]:  # Show last 10 records
                    history_text += (
                        f"• {record.date.strftime('%d.%m.%Y %H:%M')} - {record.hours_worked} ч. "
                        f"({record.status})\n"
                    )
            
            await call.message.edit_text(history_text, reply_markup=get_history_keyboard())
    await call.answer()

@dp.callback_query(F.data == "transaction_history")
async def show_transaction_history(call: CallbackQuery):
    """Show transaction history"""
    async with get_db() as db:
        employee = get_employee_by_telegram_id(db, call.from_user.id)
        if employee:
            time_records, transactions = get_employee_history(db, employee.id)
            
            if not transactions:
                history_text = "💳 История премий/штрафов пуста"
            else:
                history_text = "💳 История премий/штрафов:\n\n"
                for trans in transactions[-10:]:  # Show last 10 transactions
                    sign = "+" if trans.amount > 0 else ""
                    history_text += (
                        f"• {trans.date.strftime('%d.%m.%Y %H:%M')} - "
                        f"{sign}{trans.amount} руб. ({trans.transaction_type})\n"
                    )
            
            await call.message.edit_text(history_text, reply_markup=get_history_keyboard())
    await call.answer()

@dp.callback_query(F.data == "submit_timesheet")
async def submit_timesheet(call: CallbackQuery, state: FSMContext):
    """Start timesheet submission process"""
    await call.message.edit_text(
        "📸 Пожалуйста, отправьте фото вашего табеля.\n"
        "Я проанализирую его и посчитаю отработанные часы."
    )
    await state.set_state(TimesheetState.waiting_for_timesheet_photo)
    await call.answer()

@dp.message(TimesheetState.waiting_for_timesheet_photo, F.content_type == ContentType.PHOTO)
async def process_timesheet_photo(message: Message, state: FSMContext):
    """Process uploaded timesheet photo"""
    # Get the largest photo size
    photo = message.photo[-1]
    
    # Download the photo
    file_info = await bot.get_file(photo.file_id)
    file_path = file_info.file_path
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        await bot.download_file(file_path, tmp_file.name)
        temp_path = tmp_file.name
    
    try:
        # Process the image with OCR
        result = process_timesheet_image(temp_path)
        
        if result['success']:
            hours = result['hours']
            confidence = result['confidence']
            
            # Save to database
            async with get_db() as db:
                employee = get_employee_by_telegram_id(db, message.from_user.id)
                if employee:
                    time_record = add_time_record(db, employee.id, hours, temp_path)
                    
                    response_text = (
                        f"✅ Табель успешно загружен!\n"
                        f"Отработано часов: {hours} ч.\n"
                        f"Статус: на подтверждении\n\n"
                        f"Уверенность OCR: {confidence:.2%}"
                    )
                    
                    # Notify admin about new timesheet
                    for admin_id in ADMIN_IDS:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"🆕 Новый табель от {employee.full_name} на {hours} часов. "
                                f"Требуется подтверждение.",
                                reply_markup=get_approve_timesheet_keyboard(time_record.id)
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify admin {admin_id}: {e}")
                    
                    await message.answer(response_text, reply_markup=get_main_menu_keyboard(employee.role))
                else:
                    await message.answer("❌ Ошибка: вы не зарегистрированы.")
        else:
            await message.answer(
                f"❌ Не удалось распознать часы на изображении.\n"
                f"Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Пожалуйста, отправьте четкое фото с указанием отработанных часов."
            )
    
    except Exception as e:
        logger.error(f"Error processing timesheet photo: {e}")
        await message.answer("❌ Произошла ошибка при обработке изображения. Попробуйте снова.")
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    await state.clear()

@dp.message(TimesheetState.waiting_for_timesheet_photo)
async def wrong_file_type(message: Message, state: FSMContext):
    """Handle wrong file type during timesheet submission"""
    await message.answer("❌ Пожалуйста, отправьте фото табеля, а не текст или другой файл.")
    await state.set_state(TimesheetState.waiting_for_timesheet_photo)

# Admin panel handlers
@dp.callback_query(F.data == "admin_employees")
async def show_admin_employees(call: CallbackQuery):
    """Show admin employees management"""
    await call.message.edit_text("👥 Управление сотрудниками", reply_markup=get_admin_employees_keyboard())
    await call.answer()

@dp.callback_query(F.data == "admin_reports")
async def show_admin_reports(call: CallbackQuery):
    """Show admin reports"""
    await call.message.edit_text("📊 Отчеты", reply_markup=get_admin_reports_keyboard())
    await call.answer()

@dp.callback_query(F.data == "admin_transactions")
async def show_admin_transactions(call: CallbackQuery):
    """Show admin transactions"""
    await call.message.edit_text("💰 Премии и штрафы", reply_markup=get_admin_transactions_keyboard())
    await call.answer()

@dp.callback_query(F.data == "all_employees")
async def show_all_employees(call: CallbackQuery):
    """Show all employees"""
    async with get_db() as db:
        employees = db.query(Employee).all()
        
        if not employees:
            response_text = "👥 Нет зарегистрированных сотрудников"
        else:
            response_text = "👥 Все сотрудники:\n\n"
            for emp in employees:
                response_text += (
                    f"• {emp.full_name} (ID: {emp.telegram_id})\n"
                    f"  Должность: {emp.position or 'Не указана'}\n"
                    f"  Ставка: {emp.hourly_rate:.2f} руб./час\n"
                    f"  Баланс: {emp.balance:.2f} руб.\n"
                    f"  Роль: {emp.role}\n\n"
                )
        
        await call.message.edit_text(response_text, reply_markup=get_admin_employees_keyboard())
    await call.answer()

@dp.callback_query(F.data == "set_rates")
async def set_employee_rates(call: CallbackQuery, state: FSMContext):
    """Start process of setting employee rates"""
    async with get_db() as db:
        employees = db.query(Employee).all()
        
        if not employees:
            await call.message.edit_text("Нет сотрудников для изменения ставок.")
            return
        
        employees_text = "Выберите сотрудника для изменения ставки:\n\n"
        for i, emp in enumerate(employees, 1):
            employees_text += f"{i}. {emp.full_name} - {emp.hourly_rate:.2f} руб./час\n"
        
        await call.message.edit_text(employees_text)
        await state.set_state(AdminState.waiting_for_employee_selection)
        await call.answer()

@dp.message(AdminState.waiting_for_employee_selection)
async def select_employee_for_rate_change(message: Message, state: FSMContext):
    """Process employee selection for rate change"""
    try:
        selection = int(message.text.strip())
        
        async with get_db() as db:
            employees = db.query(Employee).all()
            
            if 1 <= selection <= len(employees):
                selected_employee = employees[selection - 1]
                await state.update_data(selected_employee_id=selected_employee.id)
                
                await message.answer(
                    f"Выбран сотрудник: {selected_employee.full_name}\n"
                    f"Текущая ставка: {selected_employee.hourly_rate:.2f} руб./час\n"
                    f"Введите новую почасовую ставку:"
                )
                await state.set_state(AdminState.waiting_for_new_rate)
            else:
                await message.answer(f"Пожалуйста, введите число от 1 до {len(employees)}")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер сотрудника.")

@dp.message(AdminState.waiting_for_new_rate)
async def set_new_rate(message: Message, state: FSMContext):
    """Process new rate setting"""
    try:
        new_rate = float(message.text.strip())
        
        if new_rate < 0:
            await message.answer("Ставка не может быть отрицательной. Введите положительное число:")
            return
        
        data = await state.get_data()
        employee_id = data.get('selected_employee_id')
        
        async with get_db() as db:
            success = update_employee_rate(db, employee_id, new_rate, message.from_user.id, "Изменение администратором")
            
            if success:
                employee = db.query(Employee).filter(Employee.id == employee_id).first()
                await message.answer(
                    f"✅ Ставка успешно изменена!\n"
                    f"Сотрудник: {employee.full_name}\n"
                    f"Новая ставка: {employee.hourly_rate:.2f} руб./час",
                    reply_markup=get_admin_employees_keyboard()
                )
            else:
                await message.answer("❌ Ошибка при изменении ставки.")
        
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для ставки:")

@dp.callback_query(F.data == "give_bonus")
async def give_bonus_start(call: CallbackQuery, state: FSMContext):
    """Start bonus giving process"""
    async with get_db() as db:
        employees = db.query(Employee).all()
        
        if not employees:
            await call.message.edit_text("Нет сотрудников для начисления премии.")
            return
        
        employees_text = "Выберите сотрудника для начисления премии:\n\n"
        for i, emp in enumerate(employees, 1):
            employees_text += f"{i}. {emp.full_name} - Баланс: {emp.balance:.2f} руб.\n"
        
        await call.message.edit_text(employees_text)
        await state.set_state(AdminState.waiting_for_employee_selection)
        # Store that we're giving a bonus, not setting a rate
        await state.update_data(action="bonus")
    await call.answer()

@dp.callback_query(F.data == "give_penalty")
async def give_penalty_start(call: CallbackQuery, state: FSMContext):
    """Start penalty giving process"""
    async with get_db() as db:
        employees = db.query(Employee).all()
        
        if not employees:
            await call.message.edit_text("Нет сотрудников для наложения штрафа.")
            return
        
        employees_text = "Выберите сотрудника для наложения штрафа:\n\n"
        for i, emp in enumerate(employees, 1):
            employees_text += f"{i}. {emp.full_name} - Баланс: {emp.balance:.2f} руб.\n"
        
        await call.message.edit_text(employees_text)
        await state.set_state(AdminState.waiting_for_employee_selection)
        # Store that we're giving a penalty, not setting a rate
        await state.update_data(action="penalty")
    await call.answer()

@dp.message(AdminState.waiting_for_employee_selection)
async def select_employee_for_transaction(message: Message, state: FSMContext):
    """Process employee selection for bonus/penalty"""
    try:
        selection = int(message.text.strip())
        
        data = await state.get_data()
        action = data.get('action')
        
        async with get_db() as db:
            employees = db.query(Employee).all()
            
            if 1 <= selection <= len(employees):
                selected_employee = employees[selection - 1]
                await state.update_data(selected_employee_id=selected_employee.id, action=action)
                
                action_text = "премии" if action == "bonus" else "штрафа"
                await message.answer(f"Введите сумму {action_text}:")
                
                # Set the correct next state based on action
                if action == "bonus":
                    await state.set_state(AdminState.waiting_for_bonus_amount)
                else:
                    await state.set_state(AdminState.waiting_for_penalty_amount)
            else:
                await message.answer(f"Пожалуйста, введите число от 1 до {len(employees)}")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер сотрудника.")

@dp.message(AdminState.waiting_for_bonus_amount)
async def process_bonus_amount(message: Message, state: FSMContext):
    """Process bonus amount"""
    try:
        amount = float(message.text.strip())
        
        if amount <= 0:
            await message.answer("Сумма премии должна быть положительной. Введите сумму:")
            return
        
        data = await state.get_data()
        employee_id = data.get('selected_employee_id')
        
        async with get_db() as db:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                transaction = add_transaction(db, employee_id, amount, 'bonus', message.from_user.id, 'Премия от администратора')
                
                # Notify employee
                try:
                    await bot.send_message(
                        employee.telegram_id,
                        f"💰 Вам начислена премия: {amount} руб.\n"
                        f"Новый баланс: {employee.balance:.2f} руб."
                    )
                except Exception:
                    pass  # Employee might not have started the bot
                
                await message.answer(
                    f"✅ Премия начислена!\n"
                    f"Сотрудник: {employee.full_name}\n"
                    f"Сумма: {amount} руб.\n"
                    f"Новый баланс: {employee.balance:.2f} руб.",
                    reply_markup=get_admin_transactions_keyboard()
                )
        
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму премии:")

@dp.message(AdminState.waiting_for_penalty_amount)
async def process_penalty_amount(message: Message, state: FSMContext):
    """Process penalty amount"""
    try:
        amount = float(message.text.strip())
        
        if amount <= 0:
            await message.answer("Сумма штрафа должна быть положительной. Введите сумму:")
            return
        
        # Make penalty amount negative
        penalty_amount = -abs(amount)
        
        data = await state.get_data()
        employee_id = data.get('selected_employee_id')
        
        async with get_db() as db:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                transaction = add_transaction(db, employee_id, penalty_amount, 'penalty', message.from_user.id, 'Штраф от администратора')
                
                # Notify employee
                try:
                    await bot.send_message(
                        employee.telegram_id,
                        f"❌ Вам начислен штраф: {abs(penalty_amount)} руб.\n"
                        f"Новый баланс: {employee.balance:.2f} руб."
                    )
                except Exception:
                    pass  # Employee might not have started the bot
                
                await message.answer(
                    f"✅ Штраф наложен!\n"
                    f"Сотрудник: {employee.full_name}\n"
                    f"Сумма: {abs(penalty_amount)} руб.\n"
                    f"Новый баланс: {employee.balance:.2f} руб.",
                    reply_markup=get_admin_transactions_keyboard()
                )
        
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму штрафа:")

# Timesheet approval handlers
@dp.callback_query(F.data.startswith("approve_timesheet_"))
async def approve_timesheet(call: CallbackQuery):
    """Approve timesheet"""
    time_record_id = int(call.data.split("_")[2])
    
    async with get_db() as db:
        time_record = db.query(TimeRecord).filter(TimeRecord.id == time_record_id).first()
        if time_record:
            time_record.status = 'approved'
            db.commit()
            
            # Update employee balance based on hours and rate
            employee = time_record.employee
            earned_amount = time_record.hours_worked * employee.hourly_rate
            employee.balance += earned_amount
            db.commit()
            
            # Notify employee
            try:
                await bot.send_message(
                    employee.telegram_id,
                    f"✅ Ваш табель на {time_record.hours_worked} часов подтвержден!\n"
                    f"Начислено: {earned_amount:.2f} руб. (ставка: {employee.hourly_rate:.2f} руб./час)\n"
                    f"Новый баланс: {employee.balance:.2f} руб."
                )
            except Exception:
                pass
    
    await call.message.edit_text(f"✅ Табель подтвержден. Начислено: {earned_amount:.2f} руб.")
    await call.answer()

@dp.callback_query(F.data.startswith("reject_timesheet_"))
async def reject_timesheet(call: CallbackQuery):
    """Reject timesheet"""
    time_record_id = int(call.data.split("_")[2])
    
    async with get_db() as db:
        time_record = db.query(TimeRecord).filter(TimeRecord.id == time_record_id).first()
        if time_record:
            time_record.status = 'rejected'
            db.commit()
            
            # Notify employee
            employee = time_record.employee
            try:
                await bot.send_message(
                    employee.telegram_id,
                    f"❌ Ваш табель на {time_record.hours_worked} часов отклонен администратором."
                )
            except Exception:
                pass
    
    await call.message.edit_text("❌ Табель отклонен.")
    await call.answer()

# Report generation handlers
@dp.callback_query(F.data == "salary_report")
async def generate_salary_report(call: CallbackQuery):
    """Generate salary report"""
    try:
        report_path = export_manager.export_salary_report()
        report_file = FSInputFile(report_path)
        
        await call.message.answer_document(
            document=report_file,
            caption="📊 Отчет по зарплатам"
        )
    except Exception as e:
        logger.error(f"Error generating salary report: {e}")
        await call.message.answer("❌ Ошибка при генерации отчета.")
    
    await call.answer()

@dp.callback_query(F.data == "hours_report")
async def generate_hours_report(call: CallbackQuery):
    """Generate hours report"""
    try:
        report_path = export_manager.export_timesheets_to_excel()
        report_file = FSInputFile(report_path)
        
        await call.message.answer_document(
            document=report_file,
            caption="⏱️ Отчет по отработанным часам"
        )
    except Exception as e:
        logger.error(f"Error generating hours report: {e}")
        await call.message.answer("❌ Ошибка при генерации отчета.")
    
    await call.answer()

@dp.callback_query(F.data == "finance_report")
async def generate_finance_report(call: CallbackQuery):
    """Generate financial report"""
    try:
        report_path = export_manager.export_transactions_to_excel()
        report_file = FSInputFile(report_path)
        
        await call.message.answer_document(
            document=report_file,
            caption="💳 Финансовый отчет (премии/штрафы)"
        )
    except Exception as e:
        logger.error(f"Error generating finance report: {e}")
        await call.message.answer("❌ Ошибка при генерации отчета.")
    
    await call.answer()

@dp.callback_query(F.data == "export_excel")
async def export_complete_report(call: CallbackQuery):
    """Export complete report with multiple sheets"""
    try:
        report_path = export_manager.export_multiple_sheets()
        report_file = FSInputFile(report_path)
        
        await call.message.answer_document(
            document=report_file,
            caption="📥 Полный отчет (все данные)"
        )
    except Exception as e:
        logger.error(f"Error exporting complete report: {e}")
        await call.message.answer("❌ Ошибка при экспорте отчета.")
    
    await call.answer()

async def main():
    """Main function to run the bot"""
    # Initialize database
    init_db()
    
    # Start scheduler
    scheduler.start()
    
    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        # Stop scheduler when bot stops
        scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())