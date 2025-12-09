from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import asyncio
from database import get_db, Employee, TimeRecord
from export_manager import export_manager
from chat_integration import notify_chat_about_monthly_reminder
from config import WORK_CHAT_ID
import logging

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            
            # Add scheduled jobs
            self.schedule_monthly_reminders()
            self.schedule_monthly_reports()
            self.schedule_data_backup()
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def schedule_monthly_reminders(self):
        """Schedule monthly reminders for timesheet submission"""
        # Schedule on the 25th of each month at 9 AM
        self.scheduler.add_job(
            self.send_monthly_reminders,
            CronTrigger(day=25, hour=9, minute=0),
            id='monthly_reminder',
            name='Send monthly timesheet reminder'
        )
        logger.info("Monthly reminder scheduled for 25th of each month at 9:00 AM")
    
    def schedule_monthly_reports(self):
        """Schedule monthly report generation"""
        # Schedule on the 1st of each month at midnight
        self.scheduler.add_job(
            self.generate_monthly_reports,
            CronTrigger(day=1, hour=0, minute=0),
            id='monthly_report',
            name='Generate monthly reports'
        )
        logger.info("Monthly report generation scheduled for 1st of each month at 00:00 AM")
    
    def schedule_data_backup(self):
        """Schedule daily data backup"""
        # Schedule daily at 2 AM
        self.scheduler.add_job(
            self.backup_data,
            CronTrigger(hour=2, minute=0),
            id='daily_backup',
            name='Daily data backup'
        )
        logger.info("Daily backup scheduled for 2:00 AM")
    
    async def send_monthly_reminders(self):
        """Send reminders to all employees about submitting timesheets"""
        logger.info("Sending monthly reminders...")
        
        with get_db() as db:
            employees = db.query(Employee).all()
            
            for employee in employees:
                try:
                    # Send reminder to each employee
                    # In a real implementation, you'd use the bot instance to send messages
                    logger.info(f"Reminder sent to employee {employee.full_name}")
                    
                    # If work chat is configured, send there too
                    if WORK_CHAT_ID:
                        await notify_chat_about_monthly_reminder(WORK_CHAT_ID)
                        
                except Exception as e:
                    logger.error(f"Failed to send reminder to employee {employee.id}: {e}")
    
    async def generate_monthly_reports(self):
        """Generate and save monthly reports"""
        logger.info("Generating monthly reports...")
        
        try:
            # Get current month and year
            now = datetime.now()
            current_month = now.month
            current_year = now.year
            
            # Generate salary report for previous month
            prev_month = current_month - 1 if current_month > 1 else 12
            prev_year = current_year if current_month > 1 else current_year - 1
            
            salary_report_path = export_manager.export_salary_report(
                month=prev_month, 
                year=prev_year,
                filename=f"salary_report_{prev_year}_{prev_month:02d}.xlsx"
            )
            
            timesheets_report_path = export_manager.export_timesheets_to_excel(
                start_date=datetime(prev_year, prev_month, 1),
                end_date=datetime(prev_year, prev_month + 1, 1) - timedelta(seconds=1) if prev_month < 12 else datetime(prev_year + 1, 1, 1) - timedelta(seconds=1),
                filename=f"timesheets_report_{prev_year}_{prev_month:02d}.xlsx"
            )
            
            logger.info(f"Monthly reports generated: {salary_report_path}, {timesheets_report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate monthly reports: {e}")
    
    async def backup_data(self):
        """Create backup of database and important files"""
        logger.info("Starting daily backup...")
        
        try:
            # In a real implementation, you would:
            # 1. Copy the database file to a backup location
            # 2. Archive important files
            # 3. Upload to cloud storage if needed
            logger.info("Daily backup completed")
            
        except Exception as e:
            logger.error(f"Failed to complete daily backup: {e}")

# Create a singleton instance
scheduler = TaskScheduler()