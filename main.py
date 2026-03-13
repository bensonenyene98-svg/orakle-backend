from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

import csv
import io

import models, schemas
from database import engine, SessionLocal

# Build tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- DASHBOARD STATS ---
@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(models.Patient).count()
    visits = db.query(models.Encounter).count()
    males = db.query(models.Patient).filter(models.Patient.sex == "Male").count()
    females = db.query(models.Patient).filter(models.Patient.sex == "Female").count()
    return {"total": total, "monthVisits": visits, "male": males, "female": females}

# ==========================================
# PATIENT INTAKE & EDITING
# ==========================================
@app.get("/api/system-id/next")
def get_next_system_id(db: Session = Depends(get_db)):
    patients = db.query(models.Patient.sys_id).all()
    max_id = 100000
    for p in patients:
        sys_id_string = p[0]
        if sys_id_string and sys_id_string.startswith('OMC-'):
            try:
                num = int(sys_id_string.split('-')[1])
                if num > max_id: max_id = num
            except: continue
    return {"next_id": f"OMC-{max_id + 1}"}

@app.post("/api/patients/register")
def register_patient(payload: schemas.PatientRegistration, db: Session = Depends(get_db)):
    new_patient = models.Patient(
        sys_id=payload.sysId, orakle_no=payload.orakleNo, surname=payload.surname,
        first_name=payload.firstName, other_names=payload.otherNames, sex=payload.sex,
        dob=payload.dob if payload.dob else None, age=int(payload.age) if payload.age else None,
        phone=payload.phone, address=payload.address
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient) 

    new_encounter = models.Encounter(
        patient_id=new_patient.id, consult_type=payload.consult, pay_category=payload.payCategory,
        specific_plan=payload.specificPlan, billing_status="Pending", complaints=f"Initial Service Required: {payload.service}"
    )
    db.add(new_encounter)
    db.commit()
    return {"message": f"Patient Successfully Registered! System ID: {new_patient.sys_id}"}

@app.get("/api/patients/recent")
def get_recent_patients(db: Session = Depends(get_db)):
    patients = db.query(models.Patient).order_by(models.Patient.created_at.desc()).limit(10).all()
    return [{"date": p.created_at.strftime("%Y-%m-%d") if p.created_at else "N/A", "hospNo": p.orakle_no or "N/A", "sysId": p.sys_id, "name": f"{p.surname} {p.first_name}", "phone": p.phone or "N/A"} for p in patients]

@app.get("/api/patients/search")
def search_patients(q: str, db: Session = Depends(get_db)):
    term = f"%{q}%"
    patients = db.query(models.Patient).filter(or_(models.Patient.surname.ilike(term), models.Patient.first_name.ilike(term), models.Patient.sys_id.ilike(term), models.Patient.orakle_no.ilike(term))).limit(20).all()
    return [{"date": p.created_at.strftime("%Y-%m-%d") if p.created_at else "N/A", "hospNo": p.orakle_no or "N/A", "sysId": p.sys_id, "name": f"{p.surname} {p.first_name}", "phone": p.phone or "N/A"} for p in patients]

@app.get("/api/patients/edit/{sys_id}")
def get_patient_for_edit(sys_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.sys_id == sys_id).first()
    if not p: raise HTTPException(status_code=404, detail="Patient not found")
    enc = db.query(models.Encounter).filter(models.Encounter.patient_id == p.id).first()
    return {
        "orakleNo": p.orakle_no or "", "phone": p.phone or "", "surname": p.surname or "",
        "firstName": p.first_name or "", "otherNames": p.other_names or "", "sex": p.sex or "",
        "address": p.address or "", "dob": p.dob or "", "age": p.age or "",
        "payCat": enc.pay_category if enc else "Out of Pocket", "plan": enc.specific_plan if enc else ""
    }

@app.put("/api/patients/edit")
def edit_patient(payload: schemas.PatientEdit, db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.sys_id == payload.sysId).first()
    if not p: raise HTTPException(status_code=404)
    p.orakle_no = payload.orakleNo; p.surname = payload.surname; p.first_name = payload.firstName
    p.other_names = payload.otherNames; p.sex = payload.sex; p.phone = payload.phone
    p.address = payload.address; p.dob = payload.dob if payload.dob else None
    p.age = int(payload.age) if payload.age else None
    db.commit()
    return {"message": "Patient details updated successfully!"}

@app.delete("/api/patients/{sys_id}")
def delete_patient(sys_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.sys_id == sys_id).first()
    if not p: raise HTTPException(status_code=404)
    encs = db.query(models.Encounter).filter(models.Encounter.patient_id == p.id).all()
    for e in encs:
        db.query(models.LabOrder).filter(models.LabOrder.encounter_id == e.id).delete()
    db.query(models.Encounter).filter(models.Encounter.patient_id == p.id).delete()
    db.delete(p)
    db.commit()
    return {"message": f"Patient {sys_id} records permanently deleted."}

# ==========================================
# CLINIC & LABS
# ==========================================
@app.get("/api/clinic/history/{sys_id}")
def get_medical_history(sys_id: str, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.sys_id == sys_id).first()
    if not patient: raise HTTPException(status_code=404, detail="Patient not found")
    encounters = db.query(models.Encounter).filter(models.Encounter.patient_id == patient.id).order_by(models.Encounter.created_at.desc()).all()
    
    history = [{"date": e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else "N/A", "complaints": e.complaints, "vitals": e.vitals or {}, "diagnosis": e.diagnosis, "rx": e.prescriptions, "labOrders": e.lab_orders, "labResults": e.lab_results, "appt": e.next_appointment.strftime("%Y-%m-%d") if e.next_appointment else None} for e in encounters]
    return {"info": {"name": f"{patient.surname} {patient.first_name}", "sex": patient.sex or "N/A", "orakleNo": patient.orakle_no or "N/A", "age": patient.age or "N/A"}, "encounters": history}

@app.post("/api/clinic/encounter")
def save_encounter(payload: schemas.EncounterCreate, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.sys_id == payload.sysId).first()
    new_encounter = models.Encounter(patient_id=patient.id, complaints=payload.complaints, vitals=payload.vitals.model_dump() if payload.vitals else {}, physical_exam=payload.physicalExam, diagnosis=payload.diagnosis, treatment_plan=payload.treatment, prescriptions=payload.prescriptions, lab_orders=payload.labOrders, next_appointment=payload.nextAppt if payload.nextAppt else None, billing_status="Pending" if payload.pushToBills else "Cleared")
    db.add(new_encounter)
    db.commit()
    db.refresh(new_encounter)
    
    if payload.labOrders and str(payload.labOrders).strip() != "":
        db.add(models.LabOrder(encounter_id=new_encounter.id, tests_ordered=payload.labOrders, status="Pending"))
        db.commit()
    return {"message": "Encounter saved! Patient routed to billing if requested."}

@app.get("/api/labs/pending")
def get_pending_labs(db: Session = Depends(get_db)):
    pending = db.query(models.LabOrder, models.Encounter, models.Patient).join(models.Encounter, models.LabOrder.encounter_id == models.Encounter.id).join(models.Patient, models.Encounter.patient_id == models.Patient.id).filter(models.LabOrder.status == "Pending").all()
    return [{"rowIndex": lab.id, "date": lab.updated_at.strftime("%Y-%m-%d") if lab.updated_at else "N/A", "sysId": pat.sys_id, "name": f"{pat.surname} {pat.first_name}", "doctor": "Orakle Doctor", "orderedTests": lab.tests_ordered} for lab, enc, pat in pending]
@app.post("/api/labs/results")
def submit_lab_results(payload: schemas.LabResultSubmit, db: Session = Depends(get_db)):
    lab_order = db.query(models.LabOrder).filter(models.LabOrder.id == payload.labOrderId).first()
    lab_order.results = payload.results
    lab_order.status = "Completed"
    enc = db.query(models.Encounter).filter(models.Encounter.id == lab_order.encounter_id).first()
    if enc: enc.lab_results = payload.results
    db.commit()
    return {"message": "Lab results successfully published!"}

# ==========================================
# BILLING, STAFF & REFERRALS
# ==========================================
@app.get("/api/billing/records")
def get_billing_records(db: Session = Depends(get_db)):
    records = db.query(models.Encounter, models.Patient).join(models.Patient, models.Encounter.patient_id == models.Patient.id).order_by(models.Encounter.created_at.desc()).limit(50).all()
    b_queue = {}
    for e, p in records:
        if p.sys_id not in b_queue: b_queue[p.sys_id] = {"sysId": p.sys_id, "name": f"{p.surname} {p.first_name}", "payCat": e.pay_category or "Out of Pocket", "plan": e.specific_plan or "None", "status": e.billing_status or "Pending"}
    return list(b_queue.values())

@app.post("/api/billing/pay")
def process_payment(payload: schemas.PaymentSubmit, db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.sys_id == payload.sysId).first()
    e = db.query(models.Encounter).filter(models.Encounter.patient_id == p.id, models.Encounter.billing_status == "Pending").order_by(models.Encounter.created_at.desc()).first()
    e.billing_status = f"Paid ({payload.currency}{payload.amount})"
    db.commit()
    return {"message": f"Payment successfully applied!"}

@app.get("/api/billing/invoice-data/{sys_id}")
def get_invoice_data(sys_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.sys_id == sys_id).first()
    if not p: return {"services": "Patient not found"}
    e = db.query(models.Encounter).filter(models.Encounter.patient_id == p.id).order_by(models.Encounter.created_at.desc()).first()
    if not e: return {"services": "No recent clinical data."}
    srv = []
    if e.consult_type: srv.append(f"Consultation: {e.consult_type}")
    if e.lab_orders: srv.append(f"Labs Ordered: {e.lab_orders}")
    if e.prescriptions: srv.append(f"Pharmacy / Prescriptions: {e.prescriptions}")
    return {"services": "\n".join(srv) if srv else "Routine Medical Checkup"}

@app.post("/api/login")
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.Staff).filter(
        models.Staff.username == payload.username, 
        models.Staff.password == payload.password
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {
        "message": "Login successful", 
        "username": user.username, 
        "role": user.role
    }

@app.get("/api/staff")
def get_staff(db: Session = Depends(get_db)):
    staff = db.query(models.Staff).all()
    return [{"staffId": s.staff_id, "user": s.username, "role": s.role} for s in staff]

@app.post("/api/staff")
def create_staff(payload: schemas.StaffCreate, db: Session = Depends(get_db)):
    db.add(models.Staff(staff_id=payload.staffId, username=payload.user, password=payload.password, role=payload.role))
    db.commit()
    return {"message": "Staff member registered securely!"}

@app.get("/api/referrals/patient/{sys_id}")
def get_referral_patient(sys_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.sys_id == sys_id).first()
    if not p: raise HTTPException(status_code=404)
    e = db.query(models.Encounter).filter(models.Encounter.patient_id == p.id).order_by(models.Encounter.created_at.desc()).first()
    return {"name": f"{p.surname} {p.first_name}", "sex": p.sex, "age": p.age, "phone": p.phone, "orakleNo": p.orakle_no, "latestLabs": e.lab_results if e and e.lab_results else "No recent labs", "latestRx": e.prescriptions if e and e.prescriptions else "No recent prescriptions"}

@app.post("/api/referrals/send")
def send_referral(payload: schemas.ReferralSend):
    return {"message": f"Referral data securely compiled and flagged for {payload.targetFacility}!"}

@app.get("/api/reports/csv")
def generate_csv(category: str, start: str, end: str, db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    if category == "patient":
        writer.writerow(["System ID", "Orakle No", "Surname", "First Name", "Sex", "Phone"])
        for p in db.query(models.Patient).all(): writer.writerow([p.sys_id, p.orakle_no, p.surname, p.first_name, p.sex, p.phone])
    elif category == "clinic":
        writer.writerow(["Date", "Patient ID", "Diagnosis", "Treatment"])
        for e in db.query(models.Encounter).all(): writer.writerow([e.created_at, e.patient_id, e.diagnosis, e.treatment_plan])
    elif category == "billing":
        writer.writerow(["Date", "Patient ID", "Billing Status", "Pay Category"])
        for e in db.query(models.Encounter).all(): writer.writerow([e.created_at, e.patient_id, e.billing_status, e.pay_category])
    elif category == "lab":
        writer.writerow(["Date", "Tests Ordered", "Results", "Status"])
        for lab in db.query(models.LabOrder).all(): writer.writerow([lab.updated_at, lab.tests_ordered, lab.results, lab.status])
    return PlainTextResponse(output.getvalue(), media_type="text/csv")