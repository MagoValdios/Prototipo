import datetime
from collections import defaultdict

from flask import Flask, redirect, render_template, request, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///allcollege.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "change-me"

db = SQLAlchemy(app)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(128), nullable=False)
    course = db.Column(db.String(64), nullable=False)
    guardian_name = db.Column(db.String(128), nullable=False)
    guardian_email = db.Column(db.String(128), nullable=False)
    guardian_password_hash = db.Column(db.String(255), nullable=False)

    attendances = db.relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    withdrawals = db.relationship("WithdrawalRecord", back_populates="student", cascade="all, delete-orphan")
    accidents = db.relationship("AccidentRecord", back_populates="student", cascade="all, delete-orphan")
    grades = db.relationship("GradeRecord", back_populates="student", cascade="all, delete-orphan")

    def set_guardian_password(self, raw_password: str) -> None:
        self.guardian_password_hash = generate_password_hash(raw_password)

    def check_guardian_password(self, raw_password: str) -> bool:
        return check_password_hash(self.guardian_password_hash, raw_password)


class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    date = db.Column(db.Date, default=datetime.date.today, nullable=False)
    status = db.Column(db.String(32), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    student = db.relationship("Student", back_populates="attendances")


class WithdrawalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    date = db.Column(db.Date, default=datetime.date.today, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    authorized_by = db.Column(db.String(128), nullable=False)

    student = db.relationship("Student", back_populates="withdrawals")


class AccidentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    date = db.Column(db.Date, default=datetime.date.today, nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(32), nullable=False)
    action_taken = db.Column(db.Text, nullable=True)

    student = db.relationship("Student", back_populates="accidents")


class GradeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject = db.Column(db.String(64), nullable=False)
    term = db.Column(db.String(32), nullable=False)
    score = db.Column(db.Float, nullable=False)

    student = db.relationship("Student", back_populates="grades")


@app.before_first_request
def create_tables() -> None:
    db.create_all()


@app.route("/")
def index():
    total_students = Student.query.count()
    course_distribution = (
        db.session.query(Student.course, db.func.count(Student.id))
        .group_by(Student.course)
        .order_by(Student.course)
        .all()
    )

    attendance_summary = compute_attendance_summary()
    accident_summary = compute_accident_summary()

    return render_template(
        "index.html",
        total_students=total_students,
        course_distribution=course_distribution,
        attendance_summary=attendance_summary,
        accident_summary=accident_summary,
    )


@app.route("/students", methods=["GET", "POST"])
def students():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        course = request.form.get("course", "").strip()
        guardian_name = request.form.get("guardian_name", "").strip()
        guardian_email = request.form.get("guardian_email", "").strip()
        guardian_password = request.form.get("guardian_password", "").strip()

        if not all([full_name, course, guardian_name, guardian_email, guardian_password]):
            flash("Todos los campos son obligatorios", "error")
        else:
            student = Student(
                full_name=full_name,
                course=course,
                guardian_name=guardian_name,
                guardian_email=guardian_email,
            )
            student.set_guardian_password(guardian_password)
            db.session.add(student)
            db.session.commit()
            flash("Alumno registrado correctamente", "success")
            return redirect(url_for("students"))

    students = Student.query.order_by(Student.full_name).all()
    course_stats = (
        db.session.query(Student.course, db.func.count(Student.id))
        .group_by(Student.course)
        .order_by(Student.course)
        .all()
    )
    return render_template("students.html", students=students, course_stats=course_stats)


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    students = Student.query.order_by(Student.full_name).all()
    if request.method == "POST":
        student_id = request.form.get("student_id")
        status = request.form.get("status")
        notes = request.form.get("notes", "").strip() or None
        date_str = request.form.get("date")

        if not student_id or not status:
            flash("Debe seleccionar un alumno y estado", "error")
        else:
            date_value = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.date.today()
            record = AttendanceRecord(
                student_id=int(student_id),
                status=status,
                notes=notes,
                date=date_value,
            )
            db.session.add(record)
            db.session.commit()
            flash("Asistencia registrada", "success")
            return redirect(url_for("attendance"))

    attendance_records = AttendanceRecord.query.order_by(AttendanceRecord.date.desc()).limit(50).all()
    attendance_summary = compute_attendance_summary()
    return render_template(
        "attendance.html",
        students=students,
        attendance_records=attendance_records,
        attendance_summary=attendance_summary,
    )


@app.route("/withdrawals", methods=["GET", "POST"])
def withdrawals():
    students = Student.query.order_by(Student.full_name).all()
    if request.method == "POST":
        student_id = request.form.get("student_id")
        authorized_by = request.form.get("authorized_by", "").strip()
        reason = request.form.get("reason", "").strip()
        date_str = request.form.get("date")

        if not student_id or not authorized_by or not reason:
            flash("Complete todos los campos", "error")
        else:
            date_value = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.date.today()
            record = WithdrawalRecord(
                student_id=int(student_id),
                date=date_value,
                authorized_by=authorized_by,
                reason=reason,
            )
            db.session.add(record)
            db.session.commit()
            flash("Retiro registrado", "success")
            return redirect(url_for("withdrawals"))

    records = WithdrawalRecord.query.order_by(WithdrawalRecord.date.desc()).limit(50).all()
    return render_template("withdrawals.html", students=students, records=records)


@app.route("/accidents", methods=["GET", "POST"])
def accidents():
    students = Student.query.order_by(Student.full_name).all()
    if request.method == "POST":
        student_id = request.form.get("student_id")
        severity = request.form.get("severity")
        description = request.form.get("description", "").strip()
        action_taken = request.form.get("action_taken", "").strip() or None
        date_str = request.form.get("date")

        if not student_id or not severity or not description:
            flash("Complete los campos obligatorios", "error")
        else:
            date_value = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.date.today()
            record = AccidentRecord(
                student_id=int(student_id),
                severity=severity,
                description=description,
                action_taken=action_taken,
                date=date_value,
            )
            db.session.add(record)
            db.session.commit()
            flash("Accidente registrado", "success")
            return redirect(url_for("accidents"))

    records = AccidentRecord.query.order_by(AccidentRecord.date.desc()).limit(50).all()
    accident_summary = compute_accident_summary()
    return render_template(
        "accidents.html",
        students=students,
        records=records,
        accident_summary=accident_summary,
    )


@app.route("/grades", methods=["GET", "POST"])
def grades():
    students = Student.query.order_by(Student.full_name).all()
    if request.method == "POST":
        student_id = request.form.get("student_id")
        subject = request.form.get("subject", "").strip()
        term = request.form.get("term", "").strip()
        score_raw = request.form.get("score", "").strip()

        if not student_id or not subject or not term or not score_raw:
            flash("Todos los campos son obligatorios", "error")
        else:
            try:
                score = float(score_raw)
            except ValueError:
                flash("La nota debe ser numérica", "error")
            else:
                record = GradeRecord(
                    student_id=int(student_id),
                    subject=subject,
                    term=term,
                    score=score,
                )
                db.session.add(record)
                db.session.commit()
                flash("Nota registrada", "success")
                return redirect(url_for("grades"))

    records = GradeRecord.query.order_by(GradeRecord.term.desc(), GradeRecord.subject).limit(50).all()
    grade_summary = compute_grade_summary()
    return render_template(
        "grades.html",
        students=students,
        records=records,
        grade_summary=grade_summary,
    )


@app.route("/parent/login", methods=["GET", "POST"])
def parent_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        student = Student.query.filter_by(guardian_email=email).first()
        if student and student.check_guardian_password(password):
            session["guardian_student_id"] = student.id
            flash("Ingreso exitoso", "success")
            return redirect(url_for("parent_dashboard"))
        flash("Credenciales inválidas", "error")

    return render_template("parent_login.html")


@app.route("/parent/dashboard")
def parent_dashboard():
    student_id = session.get("guardian_student_id")
    if not student_id:
        flash("Debe iniciar sesión", "error")
        return redirect(url_for("parent_login"))

    student = Student.query.get_or_404(student_id)

    attendance_summary = compute_attendance_summary(student_id=student_id)
    grade_summary = compute_grade_summary(student_id=student_id)
    return render_template(
        "parent_dashboard.html",
        student=student,
        attendance_summary=attendance_summary,
        grade_summary=grade_summary,
    )


@app.route("/parent/logout")
def parent_logout():
    session.pop("guardian_student_id", None)
    flash("Sesión finalizada", "success")
    return redirect(url_for("parent_login"))


def compute_attendance_summary(student_id: int | None = None):
    query = AttendanceRecord.query
    if student_id is not None:
        query = query.filter_by(student_id=student_id)
    records = query.all()

    totals = defaultdict(int)
    by_student = defaultdict(lambda: defaultdict(int))
    for record in records:
        totals[record.status] += 1
        by_student[record.student.full_name][record.status] += 1

    rates = []
    for student_name, status_counts in by_student.items():
        total = sum(status_counts.values())
        present = status_counts.get("Presente", 0)
        rate = round((present / total) * 100, 1) if total else 0
        rates.append({"student": student_name, "rate": rate, "total": total})

    return {
        "totals": dict(totals),
        "rates": sorted(rates, key=lambda item: item["student"]),
    }


def compute_accident_summary():
    rows = (
        db.session.query(AccidentRecord.severity, db.func.count(AccidentRecord.id))
        .group_by(AccidentRecord.severity)
        .order_by(AccidentRecord.severity)
        .all()
    )
    return {severity: count for severity, count in rows}


def compute_grade_summary(student_id: int | None = None):
    query = GradeRecord.query
    if student_id is not None:
        query = query.filter_by(student_id=student_id)

    rows = (
        query.with_entities(GradeRecord.student_id, GradeRecord.subject, db.func.avg(GradeRecord.score))
        .group_by(GradeRecord.student_id, GradeRecord.subject)
        .all()
    )

    summary = []
    for student_id_value, subject, avg_score in rows:
        student = Student.query.get(student_id_value)
        summary.append({
            "student": student.full_name,
            "subject": subject,
            "average": round(avg_score, 1),
        })
    return sorted(summary, key=lambda item: (item["student"], item["subject"]))


if __name__ == "__main__":
    app.run(debug=True)
