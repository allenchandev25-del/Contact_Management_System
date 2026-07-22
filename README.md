# ProContact Manager

A modern, minimalist Contact Management System built with Python, Tkinter (ttkbootstrap), and MySQL.

## Features
- **Modern UI**: Dark/Light mode support via `ttkbootstrap`.
- **Search**: Instant filtering by Name or Phone.
- **CRUD**: Full Create, Read, Update, and Delete functionality.
- **Secure**: Parameterized SQL queries to prevent injection.
- **Modular**: Clean separation of UI and Database logic.

## Prerequisites
1. **Python 3.x** installed.
2. **MySQL Server** installed and running.

## Setup Instructions

### 1. Database Setup
Open your MySQL client (Workbench, CMD, etc.) and run the contents of `setup.sql`:
```sql
CREATE DATABASE IF NOT EXISTS contact_db;
USE contact_db;
CREATE TABLE IF NOT EXISTS contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Install Dependencies
Run the following command in your terminal:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Edit `config.py` with your MySQL credentials:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'contact_db'
}
```

### 4. Run the Application
```bash
python main.py
```

## Troubleshooting
- **Connection Error**: Ensure MySQL service is running and credentials in `config.py` are correct.
- **Library Missing**: Ensure you ran `pip install ttkbootstrap mysql-connector-python`.
