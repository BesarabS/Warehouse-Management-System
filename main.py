import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import bcrypt
import jwt
import csv
import io

SECRET_KEY = "super-secret-diploma-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./warehouse.db")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="operator")

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    quantity = Column(Float, default=0.0)
    unit = Column(String)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    status = Column(String, default="active")

class TransferTransaction(Base):
    __tablename__ = "transfers"
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    quantity = Column(Float)
    date = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    username: str
    password: str = Field(..., max_length=50)

class MaterialCreate(BaseModel):
    name: str
    quantity: float
    unit: str

class ProjectCreate(BaseModel):
    name: str
    address: str

class TransferCreate(BaseModel):
    material_id: int
    quantity: float
    project_id: int

app = FastAPI(title="Система управління складом")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не вдалося перевірити облікові дані",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/api/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Користувач з таким іменем вже існує")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "Користувача успішно зареєстровано!"}

@app.post("/api/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неправильне ім'я або пароль")
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/materials")
def add_material(material: MaterialCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if material.quantity < 0:
        raise HTTPException(status_code=400, detail="Кількість не може бути від'ємною")
    new_material = Material(**material.dict())
    db.add(new_material)
    db.commit()
    return {"message": "Збережено!"}

@app.get("/api/materials")
def get_materials(db: Session = Depends(get_db)):
    return db.query(Material).all()

@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Матеріал не знайдено")
    db.delete(material)
    db.commit()
    return {"message": "Видалено!"}

@app.post("/api/projects")
def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_project = Project(**project.dict())
    db.add(new_project)
    db.commit()
    return {"message": "Об'єкт створено!"}

@app.get("/api/projects")
def get_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    result = []
    for proj in projects:
        transfers = db.query(TransferTransaction).filter(TransferTransaction.project_id == proj.id).all()
        
        summary = {}
        for t in transfers:
            mat = db.query(Material).filter(Material.id == t.material_id).first()
            if mat:
                if mat.name not in summary:
                    summary[mat.name] = {"quantity": 0.0, "unit": mat.unit}
                summary[mat.name]["quantity"] += t.quantity
        
        transfers_list = [{"material_name": name, "quantity": data["quantity"], "unit": data["unit"]} for name, data in summary.items()]
        
        result.append({
            "id": proj.id,
            "name": proj.name,
            "address": proj.address,
            "status": proj.status,
            "transfers": transfers_list
        })
    return result

@app.post("/api/projects/{project_id}/archive")
def archive_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    project.status = "archived" if project.status == "active" else "active"
    db.commit()
    return {"message": "Статус проєкту змінено"}

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    
    db.query(TransferTransaction).filter(TransferTransaction.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return {"message": "Проєкт успішно видалено"}

@app.post("/api/transfer")
def transfer_material(transfer: TransferCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    material = db.query(Material).filter(Material.id == transfer.material_id).first()
    project = db.query(Project).filter(Project.id == transfer.project_id).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Матеріал не знайдено")
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    if material.quantity < transfer.quantity:
        raise HTTPException(status_code=400, detail="Недостатньо матеріалу на складі")
        
    material.quantity -= transfer.quantity
    
    new_transfer = TransferTransaction(
        material_id=transfer.material_id,
        project_id=transfer.project_id,
        quantity=transfer.quantity
    )
    db.add(new_transfer)
    db.commit()
    return {"message": "Успішно списано!"}

@app.get("/api/analytics")
def get_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    materials = db.query(Material).all()
    forecast_data = []
    
    for mat in materials:
        transfers = db.query(TransferTransaction).filter(TransferTransaction.material_id == mat.id).order_by(TransferTransaction.date).all()
        
        if not transfers:
            continue
            
        total_transferred = sum(t.quantity for t in transfers)
        first_transfer_date = transfers[0].date
        
        days_active = (datetime.utcnow() - first_transfer_date).days
        if days_active < 1:
            days_active = 1
            
        daily_burn_rate = total_transferred / days_active
        
        if daily_burn_rate > 0:
            days_left = round(mat.quantity / daily_burn_rate)
            if days_left <= 14:
                forecast_data.append({
                    "material_name": mat.name,
                    "current_quantity": mat.quantity,
                    "unit": mat.unit,
                    "daily_burn_rate": round(daily_burn_rate, 2),
                    "days_left": days_left
                })
            
    active_projects = db.query(Project).filter(Project.status == 'active').all()
    project_distribution = []
    
    for proj in active_projects:
        proj_transfers = db.query(TransferTransaction).filter(TransferTransaction.project_id == proj.id).all()
        total_items = sum(t.quantity for t in proj_transfers)
        
        if total_items > 0:
            project_distribution.append({
                "project_name": proj.name,
                "total_received": total_items
            })
            
    return {
        "forecast": sorted(forecast_data, key=lambda x: x['days_left']), # Сортуємо від найбільш критичних
        "distribution": project_distribution
    }

@app.get("/api/reports/materials")
def export_materials_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    materials = db.query(Material).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Назва', 'Залишок', 'Одиниці виміру'])
    for mat in materials:
        writer.writerow([mat.id, mat.name, mat.quantity, mat.unit])
    output.seek(0)
    encoded_output = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    return StreamingResponse(
        encoded_output, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=materials_report.csv"}
    )

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")