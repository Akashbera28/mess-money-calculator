import os
from flask import Flask, render_template, request, send_file, jsonify
from datetime import datetime
from models import db, Expense
from calculation_utils import calculate_summary
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# -----------------------
# Config
# -----------------------
app = Flask(__name__)

# Use DATABASE_URL if available (Render provides this), otherwise fallback to sqlite
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # For some platforms the URL may start with postgres://, SQLAlchemy expects postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mess.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# initialize db
db.init_app(app)

PERSONS = ["Akash", "Suman", "Rohit", "Palash"]

# create DB tables once at startup (works for small projects)
with app.app_context():
    db.create_all()
    os.makedirs("pdfs", exist_ok=True)
    print("✅ Database initialized (URI):", app.config["SQLALCHEMY_DATABASE_URI"])

# -----------------------
# Routes
# -----------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/person", methods=["GET", "POST"])
def person():
    if request.method == "POST":
        data = request.form
        if not data.get("item") or not data.get("amount") or not data.get("date"):
            return jsonify({"error": "Missing required fields"}), 400
        try:
            amount = float(data["amount"])
            if amount <= 0:
                raise ValueError()
        except Exception:
            return jsonify({"error": "Invalid amount"}), 400
        new_expense = Expense(
            person=data["person"],
            item=data["item"],
            amount=amount,
            date=datetime.strptime(data["date"], "%Y-%m-%d"),
            notes=data.get("notes", ""),
        )
        db.session.add(new_expense)
        db.session.commit()
        return jsonify({"message": "Expense added successfully!"})
    return render_template("person.html", persons=PERSONS)

@app.route("/result")
def result():
    month = request.args.get("month")
    if not month:
        return render_template("result.html", persons=PERSONS, expenses=[], month=None)
    year, mon = map(int, month.split("-"))
    expenses = Expense.query.filter(
        db.extract("year", Expense.date) == year,
        db.extract("month", Expense.date) == mon,
    ).all()
    totals, grand_total, average, differences, settlement = calculate_summary(expenses, PERSONS)
    return render_template(
        "result.html",
        persons=PERSONS,
        expenses=expenses,
        totals=totals,
        grand_total=grand_total,
        average=average,
        differences=differences,
        settlement=settlement,
        month=month,
    )

@app.route("/generate_pdf/<month>")
def generate_pdf(month):
    year, mon = map(int, month.split("-"))
    expenses = Expense.query.filter(
        db.extract("year", Expense.date) == year,
        db.extract("month", Expense.date) == mon,
    ).all()
    totals, grand_total, average, differences, settlement = calculate_summary(expenses, PERSONS)

    os.makedirs("pdfs", exist_ok=True)
    pdf_path = f"pdfs/{month}_summary.pdf"
    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Mess Money Summary - {month}", styles["Title"]), Spacer(1, 12)]

    data = [["Date", "Person", "Item", "Amount (₹)", "Notes"]]
    for e in expenses:
        data.append([e.date.strftime("%Y-%m-%d"), e.person, e.item, f"{e.amount:.2f}", e.notes or ""])

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Grand Total: ₹{grand_total:.2f}", styles["Normal"]))
    elements.append(Paragraph(f"Average per person: ₹{average:.2f}", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Settlement Summary:", styles["Heading3"]))
    for s in settlement:
        elements.append(Paragraph(s, styles["Normal"]))

    doc.build(elements)
    return send_file(pdf_path, as_attachment=True)

# -----------------------
# Run - respects PORT env var
# -----------------------
if __name__ == "__main__":
    import os
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT, debug=True)
