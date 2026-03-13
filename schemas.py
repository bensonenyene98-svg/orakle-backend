from pydantic import BaseModel
from typing import Optional

class PatientRegistration(BaseModel):
    sysId: str
    orakleNo: Optional[str] = None
    surname: str
    firstName: str
    otherNames: Optional[str] = None
    sex: Optional[str] = None
    dob: Optional[str] = None  
    age: Optional[str] = None
    phone: str
    address: Optional[str] = None
    consult: Optional[str] = None
    service: Optional[str] = None
    payCategory: Optional[str] = None
    specificPlan: Optional[str] = None

class PatientEdit(BaseModel):
    sysId: str
    orakleNo: Optional[str] = None
    surname: str
    firstName: str
    otherNames: Optional[str] = None
    sex: Optional[str] = None
    dob: Optional[str] = None  
    age: Optional[str] = None
    phone: str
    address: Optional[str] = None
    payCat: Optional[str] = None
    plan: Optional[str] = None

class Vitals(BaseModel):
    weight: Optional[str] = None
    height: Optional[str] = None
    bpSys: Optional[str] = None
    bpDia: Optional[str] = None
    temp: Optional[str] = None
    pulse: Optional[str] = None

class EncounterCreate(BaseModel):
    sysId: str
    vitals: Optional[Vitals] = None
    complaints: Optional[str] = None
    physicalExam: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    prescriptions: Optional[str] = None
    labOrders: Optional[str] = None
    nextAppt: Optional[str] = None
    staffName: Optional[str] = "Current User"
    pushToBills: Optional[bool] = False

class LabResultSubmit(BaseModel):
    labOrderId: int
    results: str

class PaymentSubmit(BaseModel):
    sysId: str
    amount: str
    currency: str

class StaffCreate(BaseModel):
    user: str
    password: str 
    role: str
    staffId: str

class ReferralSend(BaseModel):
    sysId: str
    patientName: str
    patientSex: str
    patientAge: str
    patientPhone: str
    targetFacility: str
    specialistEmail: str
    clinicalSummary: str
    staffName: str
    refReason: str
    refReasonDisplay: str
    latestLabs: str
    latestRx: str

class InvoiceData(BaseModel):
    sysId: str
    patientName: str
    status: str
    services: str
    amount: str
    currency: str

class LoginRequest(BaseModel):
    username: str
    password: str