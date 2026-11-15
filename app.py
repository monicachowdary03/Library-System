import sqlite3
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = "change-me"
DATABASE = "library.db"
LOAN_DAYS = 14
FINE_PER_DAY = 5  # rupees


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config.get("DATABASE", DATABASE))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    with sqlite3.connect(app.config.get("DATABASE", DATABASE)) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                copies INTEGER NOT NULL DEFAULT 1 CHECK(copies >= 0));
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id),
                member_id INTEGER NOT NULL REFERENCES members(id),
                issued_on TEXT NOT NULL,
                due_on TEXT NOT NULL,
                returned_on TEXT);
        """)


def calculate_fine(due_on, returned_on=None):
    """Fine = days late * FINE_PER_DAY. Uses today's date if the book is not returned yet."""
    end = date.fromisoformat(returned_on) if returned_on else date.today()
    late_days = (end - date.fromisoformat(due_on)).days
    return max(late_days, 0) * FINE_PER_DAY


@app.route("/")
def books():
    rows = get_db().execute("SELECT * FROM books ORDER BY title").fetchall()
    return render_template("books.html", books=rows)


@app.route("/books/add", methods=["POST"])
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    try:
        copies = int(request.form.get("copies", 1))
    except ValueError:
        copies = 0
    if not title or not author or copies < 1:
        flash("Enter a title, author and at least 1 copy.", "error")
    else:
        db = get_db()
        db.execute("INSERT INTO books (title, author, copies) VALUES (?,?,?)", (title, author, copies))
        db.commit()
        flash("Book added.")
    return redirect(url_for("books"))


@app.route("/members", methods=["GET", "POST"])
def members():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not name or "@" not in email:
            flash("Enter a name and a valid email.", "error")
        else:
            try:
                db.execute("INSERT INTO members (name, email) VALUES (?,?)", (name, email))
                db.commit()
                flash("Member added.")
            except sqlite3.IntegrityError:
                flash("A member with that email already exists.", "error")
        return redirect(url_for("members"))
    return render_template("members.html", members=db.execute("SELECT * FROM members ORDER BY name").fetchall())


@app.route("/issue", methods=["GET", "POST"])
def issue():
    db = get_db()
    if request.method == "POST":
        book_id, member_id = request.form.get("book_id"), request.form.get("member_id")
        book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if book is None or book["copies"] < 1:
            flash("That book has no copies available.", "error")
            return redirect(url_for("issue"))
        today = date.today()
        db.execute("INSERT INTO loans (book_id, member_id, issued_on, due_on) VALUES (?,?,?,?)",
                   (book_id, member_id, today.isoformat(), (today + timedelta(days=LOAN_DAYS)).isoformat()))
        db.execute("UPDATE books SET copies = copies - 1 WHERE id = ?", (book_id,))
        db.commit()
        flash(f"Issued '{book['title']}'. Due in {LOAN_DAYS} days.")
        return redirect(url_for("loans"))
    return render_template("issue.html",
                           books=db.execute("SELECT * FROM books WHERE copies > 0 ORDER BY title").fetchall(),
                           members=db.execute("SELECT * FROM members ORDER BY name").fetchall())


@app.route("/loans")
def loans():
    rows = get_db().execute("""
        SELECT loans.*, books.title, members.name
        FROM loans
        JOIN books   ON books.id   = loans.book_id
        JOIN members ON members.id = loans.member_id
        ORDER BY loans.returned_on IS NOT NULL, loans.due_on""").fetchall()
    data = []
    for r in rows:
        fine = calculate_fine(r["due_on"], r["returned_on"])
        data.append({**dict(r), "fine": fine, "overdue": fine > 0 and not r["returned_on"]})
    return render_template("loans.html", loans=data)


@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id):
    db = get_db()
    loan = db.execute("SELECT * FROM loans WHERE id = ? AND returned_on IS NULL", (loan_id,)).fetchone()
    if loan is None:
        flash("Loan not found or already returned.", "error")
        return redirect(url_for("loans"))
    db.execute("UPDATE loans SET returned_on = ? WHERE id = ?", (date.today().isoformat(), loan_id))
    db.execute("UPDATE books SET copies = copies + 1 WHERE id = ?", (loan["book_id"],))
    db.commit()
    fine = calculate_fine(loan["due_on"])
    flash(f"Book returned. Fine due: ₹{fine}" if fine else "Book returned. No fine.")
    return redirect(url_for("loans"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
