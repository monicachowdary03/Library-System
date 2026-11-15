# Library Management System (Flask + SQLite)

Manage books, members and loans with automatic stock tracking and late fines.

## Features
- Relational schema: `books`, `members`, `loans` with foreign keys and constraints
- Issue / return books; stock updates automatically
- SQL `JOIN` to show loan details (book + member)
- Due dates (14 days) and fine calculation (₹5 per late day)
- Validation: no issuing out-of-stock books, unique member emails
- Unit tests with unittest

## UI
Gen-Z dark theme: aurora gradient background, glassmorphism cards, pill buttons and emoji accents (pure CSS, no JS frameworks).

## Tech
Python, Flask, SQLite, HTML, CSS (Jinja2 templates)

## Run
```bash
pip install -r requirements.txt
python app.py              # open http://127.0.0.1:5000
python -m unittest         # run tests
```
