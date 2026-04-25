from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import or_
from config import Config
from models import db, Event, User , EventUpdateLog
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from email_reader import read_email_replies
from flask_apscheduler import APScheduler



from flask_mail import Mail, Message
from ai_agent import graph   

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail()
mail.init_app(app)
db.init_app(app)

# 🔥 MAIL INIT (ADD)
BASE_URL = "http://127.0.0.1:5000"

with app.app_context():
    db.create_all()


def login_required():
    return "user_id" in session



def send_email(user_email, subject, body):
    try:
        msg = Message(
            subject=subject,
            recipients=[user_email],
            sender=app.config.get("MAIL_DEFAULT_SENDER")
        )

        
        msg.body = body

        mail.send(msg)
        print(" EMAIL SENT SUCCESSFULLY")

    except Exception as e:
        print(" MAIL ERROR:", str(e))
@app.route("/")
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    try:
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("All fields required", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        flash("Login successful", "success")
        return redirect(url_for("index"))

    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()

            if not email or not password:
                flash("All fields required", "danger")
                return redirect(url_for("register"))

            if len(password) < 6:
                flash("Password must be at least 6 characters", "danger")
                return redirect(url_for("register"))

            if User.query.filter_by(email=email).first():
                flash("Email already exists", "danger")
                return redirect(url_for("register"))

            user = User(email=email, password=generate_password_hash(password))

            db.session.add(user)
            db.session.commit()

            # AUTO EMAIL (
            send_email(
                email,
                "Welcome ",
                "Thanks for registering in Event Manager System"
            )

            flash("Registered successfully", "success")
            return redirect(url_for("login"))

        except Exception as e:
            db.session.rollback()
            flash(str(e), "danger")

    return render_template("register.html")


@app.route("/events")
def index():

    if not login_required():
        return redirect(url_for("login"))

    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 5))
        search = request.args.get("search", "")

        query = Event.query

        if search:
            query = query.filter(
                or_(
                    Event.id.like(f"%{search}%"),
                    Event.name.ilike(f"%{search}%"),
                    Event.date.like(f"%{search}%"),
                    Event.location.ilike(f"%{search}%")
                )
            )

        total = query.count()

        events = query.order_by(Event.id.desc()) \
                      .limit(size) \
                      .offset((page - 1) * size) \
                      .all()

        for e in events:
            if isinstance(e.date, str):
                e.date = datetime.strptime(e.date, "%Y-%m-%d").strftime("%d-%m-%Y")
            else:
                e.date = e.date.strftime("%d-%m-%Y")

        return render_template(
            "events.html",
            events=events,
            page=page,
            size=size,
            total=total,
            search=search
        )

    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("login"))

#
BASE_URL = "http://127.0.0.1:5000"







@app.route("/add", methods=["GET", "POST"])
def add_event():

    if not login_required():
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            date_str = request.form.get("date", "").strip()
            location = request.form.get("location", "").strip()
            description = request.form.get("description", "").strip()

           
            #  MISSING FIELD CHECK
          
            missing = []
            if not name:
                missing.append("Name")
            if not date_str:
                missing.append("Date")
            if not location:
                missing.append("Location")

            
            # EMAIL IF REQUIRED FIELDS MISSING
            
            if missing:
                user = User.query.get(session["user_id"])

                send_email(
                    user.email,
                    "Incomplete Event ",
                    f"""Hello 

You tried to create an event but some required fields are missing.

 Missing Fields:
{', '.join(missing)}

Please fill them and try again.

— Event AI Agent 
"""
                )

                flash("Please fill all required fields", "danger")
                return redirect(url_for("add_event"))

            
            # VALIDATION
           
            if len(name) < 3:
                flash("Name must be at least 3 characters", "danger")
                return redirect(url_for("add_event"))

            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if event_date < datetime.now().date():
                flash("Past date not allowed", "danger")
                return redirect(url_for("add_event"))

            # SAVE EVENT
            
            event = Event(
                name=name,
                date=event_date,
                location=location,
                description=description,
                created_by=session["user_id"]
            )

            db.session.add(event)
            db.session.commit()

            
            #  EMAIL IF DESCRIPTION MISSING (UPDATED )
          
            if not description:
                user = User.query.get(session["user_id"])

                edit_link = f"{BASE_URL}/edit/{event.id}"

                print(" LINK:", edit_link)  # debug

                send_email(
                    user.email,
                    "Complete Your Event Details ",
                    f"""Hello 

Your event '{name}' is created successfully.

Missing Field:
 Description

You can reply to this email like:
Description: Birthday party
Location: Pune

OR update directly here:
 {edit_link}

(Event ID: {event.id})

— Event AI Agent 
"""
                )

            flash("Event added successfully", "success")
            return redirect(url_for("index"))

        except Exception as e:
            db.session.rollback()
            flash(str(e), "danger")

    return render_template("add_event.html")

# AI CHAT ROUTE 
@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()
    query = data.get("message")

    result = graph.invoke({
        "query": query,
        "user_id": session.get("user_id")
    })

    return {"response": result.get("response")}


@app.route("/chat-ui")
def chat_ui():
    if not login_required():
        return redirect(url_for("login"))
    return render_template("chat.html")



@app.route("/read-mails")
def read_mails():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Function se results mangwao
    results = read_email_replies(app, session["user_id"])

    return render_template("sync_results.html", results=results)



scheduler = APScheduler()

def auto_read_mails():
    with app.app_context():
        print(" Auto email sync running...")
        users = User.query.all()
        for user in users:
            read_email_replies(app, user.id)

def start_scheduler(app):
    scheduler.init_app(app)

    scheduler.add_job(
    id="email_job",
    func=auto_read_mails,
    trigger="interval",
    minutes=5,
    max_instances=1,
    coalesce=True
)
    scheduler.start()




@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_event(id):

    if not login_required():
        return redirect(url_for("login"))

    event = Event.query.get_or_404(id)

    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            date_str = request.form.get("date", "").strip()
            location = request.form.get("location", "").strip()
            description = request.form.get("description", "").strip()

            if not name or not date_str or not location:
                flash("All fields required", "danger")
                return redirect(url_for("edit_event", id=id))

            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            event.name = name
            event.date = event_date
            event.location = location
            event.description = description

            db.session.commit()

            flash("Event updated successfully", "success")
            return redirect(url_for("index"))

        except Exception as e:
            db.session.rollback()
            flash(str(e), "danger")

    return render_template("edit_event.html", event=event)


@app.route("/view/<int:id>")
def view_event(id):
    event = Event.query.get_or_404(id)
    return render_template("view.html", event=event)

@app.route("/delete/<int:id>", methods=["POST"])
def delete_event(id):

    if not login_required():
        return redirect(url_for("login"))

    try:
        event = Event.query.get_or_404(id)
        db.session.delete(event)
        db.session.commit()

        flash("Deleted successfully", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("index"))


@app.route("/event-history")
def event_history():
    logs = EventUpdateLog.query.order_by(EventUpdateLog.created_at.desc()).all()
    return render_template("event_history.html", logs=logs)


start_scheduler(app)

if __name__ == "__main__":
    app.run(debug=True)