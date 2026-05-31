# ERPInsight — Setup Guide

## 1. Prerequisites
- Python 3.10+
- MySQL 8.0+
- pip

## 2. Create Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

## 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## 4. Create MySQL Database
Open MySQL and run:
```sql
CREATE DATABASE erpinsight_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 5. Configure Database
Edit `erpinsight/settings.py` and update:
```python
DATABASES = {
    'default': {
        'NAME': 'erpinsight_db',
        'USER': 'your_mysql_username',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

## 6. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## 7. Create Super Admin
```bash
python manage.py createsuperuser
# Follow prompts — use role: super_admin
```
After creation, go to /admin and set the user's role to `super_admin`.

## 8. Run Development Server
```bash
python manage.py runserver
```
Open: http://127.0.0.1:8000

---

## User Flow

### Super Admin
1. Log in at `/accounts/login/`
2. Register a company via `/admin/` (for now)
3. Share the generated company code (e.g. ERP-OD-1001) with Admin offline

### Admin
1. Go to `/accounts/signup/admin/`
2. Enter company code + create account
3. Log in → Admin Dashboard

### Employee
1. Admin must register employee email first (via admin panel for now)
2. Employee goes to `/accounts/signup/employee/`
3. Enter registered email + create account
4. Log in → Employee Dashboard

---

## Project Structure
```
erpinsight/
├── manage.py
├── requirements.txt
├── erpinsight/          ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/            ← Auth & user management app
│   ├── models.py        ← CustomUser, Company, RegisteredEmployee
│   ├── views.py         ← Login, signup, dashboards
│   ├── forms.py         ← All auth forms
│   ├── urls.py          ← URL routes
│   └── admin.py         ← Django admin config
└── templates/
    ├── base.html         ← AdminLTE sidebar layout
    ├── auth_base.html    ← Login/signup layout
    └── accounts/
        ├── login.html
        ├── admin_signup.html
        ├── employee_signup.html
        ├── change_password.html
        ├── super_admin_dashboard.html
        ├── admin_dashboard.html
        └── employee_dashboard.html
```
