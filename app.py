from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import or_
from config import Config
from models import db, Event, User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from datetime import datetime  

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()



def login_required():
    return "user_id" in session



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

        events = query.order_by(Event.id.asc()) \
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



from datetime import datetime

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
            

            if not name or len(name) < 3:
                flash("Name must be at least 3 characters", "danger")
                return redirect(url_for("add_event"))

            if not date_str:
                flash("Date is required", "danger")
                return redirect(url_for("add_event"))

            if not location:
                flash("Location is required", "danger")
                return redirect(url_for("add_event"))

            
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if event_date < datetime.now().date():
                flash("Past date not allowed", "danger")
                return redirect(url_for("add_event"))

            event = Event(
                name=name,
                date=event_date,   
                location=location,
                description=description,
                
            )

            db.session.add(event)
            db.session.commit()

            flash("Event added successfully", "success")
            return redirect(url_for("index"))

        except Exception as e:
            db.session.rollback()
            flash(str(e), "danger")

    return render_template("add_event.html")


from datetime import datetime

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_event(id):

    if not login_required():
        return redirect(url_for("login"))

    try:
        event = Event.query.get_or_404(id)

        if request.method == "POST":

            name = request.form.get("name", "").strip()
            date_str = request.form.get("date", "").strip()   
            location = request.form.get("location", "").strip()
            description = request.form.get("description", "").strip()

            if not name or len(name) < 3:
                flash("Invalid name", "danger")
                return redirect(url_for("edit_event", id=id))

            if not date_str:
                flash("Date required", "danger")
                return redirect(url_for("edit_event", id=id))

            if not location:
                flash("Location required", "danger")
                return redirect(url_for("edit_event", id=id))

            
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()

           
            if event_date < datetime.now().date():
                flash("Past date not allowed", "danger")
                return redirect(url_for("edit_event", id=id))

           
            event.name = name
            event.date = event_date
            event.location = location
            event.description = description

            db.session.commit()

            flash("Event updated successfully", "success")
            return redirect(url_for("index"))

        return render_template("edit_event.html", event=event)

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")
        return redirect(url_for("index"))

@app.route("/delete/<int:id>", methods=["POST"])
def delete_event(id):

    if not login_required():
        return redirect(url_for("login"))

    try:
        event = Event.query.get_or_404(id)

        db.session.delete(event)
        db.session.commit()

        flash("Event deleted successfully", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("index"))



@app.route("/view/<int:id>")
def view_event(id):

    if not login_required():
        return redirect(url_for("login"))

    event = Event.query.get_or_404(id)
    return render_template("view.html", event=event)



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run(debug=True)