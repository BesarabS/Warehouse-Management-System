# Warehouse-Management-System

## Інструкція із запуску

Для роботи системи потрібен встановлений [Docker](https://docs.docker.com/get-docker/) та Docker Compose, або Python 3.9+ для локального запуску.

### Спосіб 1: Запуск через Docker (Рекомендовано)
Цей спосіб автоматично завантажить необхідні образи, налаштує базу даних PostgreSQL та запустить сервер.

1. Запустіть контейнер у фоновому режимі:
```
docker-compose up --build -d
```

2. Відкрийте застосунок у браузері за адресою: http://localhost:8000

### Спосіб 2: Локальний запуск (для Developer)

1. Створіть та активуйте віртуальне середовище:
```
python -m venv venv
# Для Windows: venv\Scripts\activate
# Для Linux/macOS: source venv/bin/activate
```

2. Встановіть залежності:
```
pip install -r requirements.txt
```

3. Запустіть локальний сервер за допомогою Uvicorn:
```
uvicorn main:app --reload
```

4. Відкрийте застосунок у браузері: http://127.0.0.1:8000
