from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime
from database import Base

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    sys_id = Column(String, unique=True, index=True)
    orakle_no = Column(String, index=True, nullable=True)
    surname = Column(String)
    first_name = Column(String)
    other_names = Column(String, nullable=True)
    sex = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    phone = Column(String)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Encounter(Base):
    __tablename__ = "encounters"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    consult_type = Column(String, nullable=True)
    pay_category = Column(String, nullable=True)
    specific_plan = Column(String, nullable=True)
    billing_status = Column(String, default="Pending")
    complaints = Column(String, nullable=True)
    vitals = Column(JSON, nullable=True)
    physical_exam = Column(String, nullable=True)
    diagnosis = Column(String, nullable=True)
    treatment_plan = Column(String, nullable=True)
    prescriptions = Column(String, nullable=True)
    lab_orders = Column(String, nullable=True)
    lab_results = Column(String, nullable=True)
    next_appointment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabOrder(Base):
    __tablename__ = "lab_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"))
    tests_ordered = Column(String)
    results = Column(String, nullable=True)
    status = Column(String, default="Pending")
    # We must use updated_at because that is what Neon has!
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Staff(Base):
    __tablename__ = "staff"
    
    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(String, unique=True, index=True)
    username = Column(String)
    password = Column(String)
    role = Column(String)