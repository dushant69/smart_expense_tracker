# 💰 Expense Tracker (Django)

A simple web app where each user can log in and track their personal expenses.
Built with Django + SQLite + Bootstrap.

## Features
- User **signup / login / logout** (each user sees only their own expenses)
- **Add, edit, delete** expenses (full CRUD)
- Dashboard with **total spent**, **entry count**, and **spending-by-category** breakdown
- Django **admin panel** to manage all data
- Clean, responsive **Bootstrap** UI

---

## How to run

```bash
# from inside the expense_tracker_project folder
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** in your browser.

- App: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/  →  **admin / admin12345**

(If you ever reset the database, run `python manage.py migrate` first, then
`python manage.py createsuperuser` to make a new admin.)

---

## Project structure

```
expense_tracker_project/
├── manage.py                 # Django command-line tool
├── db.sqlite3                # the database (created after migrate)
├── expense_tracker/          # project config
│   ├── settings.py           # installed apps, DB, templates, auth redirects
│   └── urls.py               # top-level URL routing
├── expenses/                 # our app
│   ├── models.py             # Expense model (the database table)
│   ├── views.py              # the logic for each page
│   ├── forms.py              # ExpenseForm + SignUpForm
│   ├── urls.py               # app URL routing
│   └── admin.py              # registers Expense in the admin panel
└── templates/                # all HTML pages
    ├── base.html             # shared layout (navbar, Bootstrap)
    ├── registration/         # login + signup pages
    └── expenses/             # dashboard, form, delete-confirm
```

---

## How it works (the MVT flow)

Django uses **Model – View – Template**:

1. **Model** (`models.py`) — defines the `Expense` table in the database.
2. **View** (`views.py`) — a Python function that runs when a URL is visited;
   it fetches/saves data and picks a template.
3. **Template** (`templates/`) — the HTML shown to the user.

Example: visiting `/` → `dashboard` view → queries the user's expenses →
renders `dashboard.html`.

---

## 🎤 Likely questions & answers (for the presentation)

**Q: What is Django?**
A high-level Python web framework that handles databases, URLs, forms, and
security so you can build web apps quickly.

**Q: What is the MVT architecture?**
Model (data), View (logic), Template (HTML). Django's version of MVC.

**Q: What is a model? / What does `models.py` do?**
A Python class that maps to a database table. Each attribute is a column.
My `Expense` model has title, amount, category, date, notes, and a link to the user.

**Q: What are migrations?**
`makemigrations` turns model changes into instructions; `migrate` applies them
to the database. It's how Django creates/updates tables without writing SQL.

**Q: How does login work? How do you keep each user's data separate?**
I use Django's built-in authentication. In the views I filter with
`Expense.objects.filter(user=request.user)`, so a user only ever sees their own
expenses. Pages use the `@login_required` decorator to block anonymous users.

**Q: What is a ForeignKey?**
It creates a relationship between tables. `Expense.user` is a ForeignKey to
`User`, meaning each expense belongs to one user (one-to-many).

**Q: What is CSRF? Why `{% csrf_token %}`?**
Cross-Site Request Forgery protection. Django requires a token in every POST
form so attackers can't submit forms on the user's behalf.

**Q: What is a ModelForm?**
A form auto-generated from a model. `ExpenseForm` builds the fields from the
`Expense` model, and handles validation and saving for me.

**Q: What is the ORM?**
Object-Relational Mapper — lets me query the database with Python
(`Expense.objects.filter(...)`) instead of raw SQL.

**Q: How is the total / category breakdown calculated?**
Using the ORM's aggregation: `aggregate(Sum('amount'))` for the total and
`.values('category').annotate(total=Sum('amount'))` for the breakdown.

**Q: Which database are you using?**
SQLite — Django's default, a single file (`db.sqlite3`). For production you'd
switch to PostgreSQL/MySQL by changing one setting.

**Q: What would you add next?**
Charts (e.g. a pie chart of categories), date filtering, monthly budgets,
and exporting to CSV.
