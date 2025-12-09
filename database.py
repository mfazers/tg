from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class Employee(Base):
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    position = Column(String(255))
    hourly_rate = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    role = Column(String(50), default='employee')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    time_records = relationship("TimeRecord", back_populates="employee")
    transactions = relationship("Transaction", back_populates="employee")
    rate_changes = relationship("RateChange", back_populates="employee")

class TimeRecord(Base):
    __tablename__ = 'time_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    hours_worked = Column(Float, nullable=False)
    status = Column(String(50), default='pending')  # pending, approved, rejected
    file_path = Column(String(500))  # Path to uploaded image
    comment = Column(Text)
    
    # Relationship
    employee = relationship("Employee", back_populates="time_records")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    amount = Column(Float, nullable=False)  # Positive for bonuses, negative for penalties
    transaction_type = Column(String(50), nullable=False)  # bonus, penalty
    date = Column(DateTime, default=datetime.utcnow)
    comment = Column(Text)
    processed_by = Column(Integer)  # Telegram ID of admin who processed
    
    # Relationship
    employee = relationship("Employee", back_populates="transactions")

class RateChange(Base):
    __tablename__ = 'rate_changes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    old_rate = Column(Float, nullable=False)
    new_rate = Column(Float, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(Integer)  # Telegram ID of admin who changed
    comment = Column(Text)
    
    # Relationship
    employee = relationship("Employee", back_populates="rate_changes")

class ChatIntegration(Base):
    __tablename__ = 'chat_integrations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    chat_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)



# Create engine and session
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///employees.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize the database and create tables if they don't exist"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Additional utility functions
def get_employee_by_telegram_id(db, telegram_id):
    """Get employee by their Telegram ID"""
    return db.query(Employee).filter(Employee.telegram_id == telegram_id).first()

def create_employee(db, telegram_id, full_name, position=None):
    """Create a new employee"""
    employee = Employee(
        telegram_id=telegram_id,
        full_name=full_name,
        position=position,
        role='employee'
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

def update_employee_rate(db, employee_id, new_rate, admin_telegram_id, comment=None):
    """Update employee's hourly rate and log the change"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee:
        # Log the rate change
        rate_change = RateChange(
            employee_id=employee_id,
            old_rate=employee.hourly_rate,
            new_rate=new_rate,
            changed_by=admin_telegram_id,
            comment=comment
        )
        db.add(rate_change)
        
        # Update employee rate
        employee.hourly_rate = new_rate
        db.commit()
        return True
    return False

def add_transaction(db, employee_id, amount, transaction_type, admin_telegram_id, comment=None):
    """Add a bonus or penalty transaction"""
    transaction = Transaction(
        employee_id=employee_id,
        amount=amount,
        transaction_type=transaction_type,
        processed_by=admin_telegram_id,
        comment=comment
    )
    db.add(transaction)
    
    # Update employee balance
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee:
        employee.balance += amount
    
    db.commit()
    return transaction

def add_time_record(db, employee_id, hours_worked, file_path=None, comment=None):
    """Add a time record for an employee"""
    time_record = TimeRecord(
        employee_id=employee_id,
        hours_worked=hours_worked,
        file_path=file_path,
        comment=comment
    )
    db.add(time_record)
    db.commit()
    return time_record

def get_employee_history(db, employee_id):
    """Get time records and transactions for an employee"""
    time_records = db.query(TimeRecord).filter(TimeRecord.employee_id == employee_id).all()
    transactions = db.query(Transaction).filter(Transaction.employee_id == employee_id).all()
    return time_records, transactions