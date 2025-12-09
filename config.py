import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///employees.db')

# Chat integration
WORK_CHAT_ID = os.getenv('WORK_CHAT_ID')  # Optional: specific chat ID for work notifications
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []

# OCR Configuration
TESSERACT_PATH = os.getenv('TESSERACT_PATH', '/usr/bin/tesseract')  # Path to tesseract executable

# Export settings
EXPORT_DIR = os.getenv('EXPORT_DIR', './exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

# Roles
EMPLOYEE_ROLE = 'employee'
ADMIN_ROLE = 'admin'

# File processing settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']

print(f"Configuration loaded. Admin IDs: {ADMIN_IDS}")