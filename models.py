from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)   
    created_by = db.Column(db.Integer, nullable=True)



class EventUpdateLog(db.Model):
    __tablename__ = "event_update_log"

    id = db.Column(db.Integer, primary_key=True)

    #  linked event
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

    #  snapshot of updated data
    name = db.Column(db.String(100))
    date = db.Column(db.Date)
    location = db.Column(db.String(100))
    description = db.Column(db.Text)

    #  what fields were changed
    fields_changed = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)