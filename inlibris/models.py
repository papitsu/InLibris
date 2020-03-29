import click
import json
import re
from datetime import datetime
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
from inlibris import db

@click.command("init-db")
@with_appcontext
def init_db_command():
    db.create_all()
    from inlibris.utils import _populate_db
    _populate_db(db)
    click.echo('Initialized the database.')

@click.command("reset-db")
@with_appcontext
def reset_db_command():
    db.reflect()
    db.drop_all()
    db.create_all()
    from inlibris.utils import _populate_db
    _populate_db(db)
    click.echo('Reseted the database.')


class Patron(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    barcode = db.Column(db.Integer, unique=True, nullable=False)
    firstname = db.Column(db.String(64), nullable=False)
    lastname = db.Column(db.String(64), default=None)
    email = db.Column(db.String(64), unique=True, nullable=False)
    group = db.Column(db.String(64), nullable=False, default="Customer")
    status = db.Column(db.String(64), nullable=False, default="Active")
    regdate = db.Column(db.DateTime, nullable=False)
    
    loans = db.relationship("Loan", back_populates="patron")
    holds = db.relationship("Hold", back_populates="patron")

class Book(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    barcode = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(64), nullable=False)
    author = db.Column(db.String(64), default=None)
    pubyear = db.Column(db.Integer, nullable=False)
    format = db.Column(db.String(64), default="book", nullable=False)
    description = db.Column(db.String(512), nullable=False, default="")
    loantime = db.Column(db.Integer, nullable=False, default=28)
    renewlimit = db.Column(db.Integer, nullable=False, default=10)
    
    loan = db.relationship("Loan", cascade="all, delete-orphan", back_populates="book")
    holds = db.relationship("Hold", cascade="all, delete-orphan", back_populates="book")

class Loan(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id", ondelete="CASCADE"), unique=True)
    patron_id = db.Column(db.Integer, db.ForeignKey("patron.id"))
    loandate = db.Column(db.DateTime, nullable=False)
    renewaldate = db.Column(db.DateTime, default=None)
    duedate = db.Column(db.DateTime, nullable=False)
    renewed = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(64), default="Charged", nullable=False)
    
    book = db.relationship("Book", back_populates="loan")
    patron = db.relationship("Patron", back_populates="loans")

class Hold(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id", ondelete="CASCADE"))
    patron_id = db.Column(db.Integer, db.ForeignKey("patron.id"))
    holddate = db.Column(db.DateTime, nullable=False)
    expirationdate = db.Column(db.DateTime, nullable=False)
    pickupdate = db.Column(db.DateTime, default=None)
    status = db.Column(db.String(64), default="Requested", nullable=False)
    
    book = db.relationship("Book", back_populates="holds")
    patron = db.relationship("Patron", back_populates="holds")