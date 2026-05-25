import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db, Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_register_user_success():
    response = client.post(
        "/api/register",
        json={"username": "testadmin", "password": "supersecret123"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Користувача успішно зареєстровано!"

def test_login_user_success():
    client.post("/api/register", json={"username": "testadmin", "password": "supersecret123"})
    response = client.post(
        "/api/login",
        data={"username": "testadmin", "password": "supersecret123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_add_material_unauthorized():
    response = client.post(
        "/api/materials",
        json={"name": "Цемент", "quantity": 50, "unit": "мішок"}
    )
    assert response.status_code == 401

def test_add_material_authorized():
    client.post("/api/register", json={"username": "testadmin", "password": "supersecret123"})
    login_response = client.post("/api/login", data={"username": "testadmin", "password": "supersecret123"})
    token = login_response.json()["access_token"]
    
    response = client.post(
        "/api/materials",
        json={"name": "Цемент", "quantity": 50, "unit": "мішок"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Збережено!"

def test_create_and_get_projects():
    client.post("/api/register", json={"username": "testadmin", "password": "supersecret123"})
    token = client.post("/api/login", data={"username": "testadmin", "password": "supersecret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response_post = client.post(
        "/api/projects",
        json={"name": "ЖК Академічний", "address": "вул. Наукова, 10"},
        headers=headers
    )
    assert response_post.status_code == 200
    
    response_get = client.get("/api/projects", headers=headers)
    assert response_get.status_code == 200
    projects = response_get.json()
    assert len(projects) == 1
    assert projects[0]["name"] == "ЖК Академічний"
    assert projects[0]["status"] == "active"

def test_transfer_material_business_logic():
    client.post("/api/register", json={"username": "testadmin", "password": "supersecret123"})
    token = client.post("/api/login", data={"username": "testadmin", "password": "supersecret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    client.post("/api/materials", json={"name": "Пісок", "quantity": 100, "unit": "т"}, headers=headers)
    client.post("/api/projects", json={"name": "Об'єкт №1", "address": "Центр"}, headers=headers)
    
    transfer_response = client.post(
        "/api/transfer",
        json={"material_id": 1, "project_id": 1, "quantity": 20},
        headers=headers
    )
    assert transfer_response.status_code == 200
    
    materials_response = client.get("/api/materials", headers=headers)
    updated_material = materials_response.json()[0]
    assert updated_material["quantity"] == 80.0

def test_analytics_endpoint():
    client.post("/api/register", json={"username": "testadmin", "password": "supersecret123"})
    token = client.post("/api/login", data={"username": "testadmin", "password": "supersecret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "forecast" in data
    assert "distribution" in data
    assert isinstance(data["forecast"], list)
    assert isinstance(data["distribution"], list)