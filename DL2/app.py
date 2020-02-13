import json
import re
from datetime import datetime
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Patron(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    barcode = db.Column(db.String(6), unique=True, nullable=False)
    firstname = db.Column(db.String(64), nullable=False)
    lastname = db.Column(db.String(64), default=None)
    email = db.Column(db.String(64), unique=True, nullable=False)
    group = db.Column(db.String(64), nullable=False, default="Customer")
    status = db.Column(db.String(64), nullable=False, default="Active")
    regdate = db.Column(db.DateTime, nullable=False)
    
    loans = db.relationship("Loan", back_populates="patron")
    holds = db.relationship("Hold", back_populates="patron")

class Item(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    barcode = db.Column(db.String(6), unique=True, nullable=False)
    title = db.Column(db.String(64), nullable=False)
    author = db.Column(db.String(64), default=None)
    pubyear = db.Column(db.Integer, nullable=False)
    format = db.Column(db.String(64), default="book", nullable=False)
    description = db.Column(db.String(512), nullable=False, default="")
    catdate = db.Column(db.DateTime, nullable=False)
    loantime = db.Column(db.Integer, nullable=False, default=28)
    renewlimit = db.Column(db.Integer, nullable=False, default=10)
    
    loan = db.relationship("Loan", cascade="all, delete-orphan", back_populates="item")
    holds = db.relationship("Hold", cascade="all, delete-orphan", back_populates="item")

class Loan(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id", ondelete="CASCADE"), unique=True)
    patron_id = db.Column(db.Integer, db.ForeignKey("patron.id"))
    loandate = db.Column(db.DateTime, nullable=False)
    renewaldate = db.Column(db.DateTime, default=None)
    duedate = db.Column(db.DateTime, nullable=False)
    renewed = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(64), default="Charged", nullable=False)
    
    item = db.relationship("Item", back_populates="loan")
    patron = db.relationship("Patron", back_populates="loans")

class Hold(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id", ondelete="CASCADE"))
    patron_id = db.Column(db.Integer, db.ForeignKey("patron.id"))
    holddate = db.Column(db.DateTime, nullable=False)
    expirationdate = db.Column(db.DateTime, nullable=False)
    pickupdate = db.Column(db.DateTime, default=None)
    status = db.Column(db.String(64), default="Requested", nullable=False)
    
    item = db.relationship("Item", back_populates="holds")
    patron = db.relationship("Patron", back_populates="holds")

@app.route("/hello/<name>/")
def hello(name):
    return "Hello {}".format(name)

@app.route("/patrons/add/", methods=["POST"])
def add_patron():

    # Rough email validation from here:
    # https://stackoverflow.com/questions/8022530/how-to-check-for-valid-email-address
    EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

    if request.json == None:
        return "Request content type must be JSON", 415
    if request.method != "POST":
        return "POST method required", 405
    if ("barcode" or "firstname" or "email") not in request.json:
        return "Incomplete request - missing fields", 400
    if not (isinstance(request.json["barcode"], str) and isinstance(request.json["firstname"], str) and isinstance(request.json["email"], str)):
        return "Barcode, name and email must be strings", 400
    if not EMAIL_REGEX.match(request.json["email"]):
        return "Email not valid", 400
    try:
        barcode = request.json["barcode"]
        firstname = request.json["firstname"]
        email = request.json["email"]

        if "lastname" in request.json and isinstance(request.json["lastname"], str):
            lastname = request.json["lastname"]
        else:
            lastname = None

        if "group" in request.json and isinstance(request.json["group"], str):
            group = request.json["group"]
        else:
            group = "Customer"

        if "status" in request.json and isinstance(request.json["status"], str):
            status = request.json["status"]
        else:
            status = "Active"

        patron = Patron(
            barcode=barcode,
            firstname=firstname,
            lastname=lastname,
            email=email,
            group=group,
            status=status,
            regdate=datetime.now()
        )

        db.session.add(patron)
        db.session.commit()
        return "", 201
    except Exception as e:
        return str(e), 409

@app.route("/patrons/", methods=["GET"])
def get_patrons():
    if request.method != "GET":
        return "GET method required", 405

    patrons = Patron.query.all()
    
    patronList = []

    for patron in patrons:
        patronInfo = {}
        patronInfo['barcode'] = patron.barcode
        patronInfo['firstname'] = patron.firstname
        patronInfo['lastname'] = patron.lastname
        patronInfo['email'] = patron.email
        patronInfo['group'] = patron.group
        patronInfo['status'] = patron.status
        patronInfo['regdate'] = patron.regdate
        patronList.append(patronInfo)

    return json.dumps(patronList, indent=4, default=str), 200

@app.route("/items/add/", methods=["POST"])
def add_item():

    if request.json == None:
        return "Request content type must be JSON", 415
    if request.method != "POST":
        return "POST method required", 405

    if ("barcode" or "title" or "pubyear") not in request.json:
        return "Incomplete request - missing fields", 400
    if not (isinstance(request.json["barcode"], str) and isinstance(request.json["title"], str) and isinstance(request.json["pubyear"], str)):
        return "Barcode, title and pubyear must be strings", 400
    try:
        barcode = request.json["barcode"]
        title = request.json["title"]
        pubyear = request.json["pubyear"]

        if "author" in request.json and isinstance(request.json["author"], str):
            author = request.json["author"]
        else:
            author = None

        if "format" in request.json and isinstance(request.json["format"], str):
            format = request.json["format"]
        else:
            format = "book"

        if "description" in request.json and isinstance(request.json["description"], str):
            description = request.json["description"]
        else:
            description = ""

        if "loantime" in request.json and isinstance(request.json["loantime"], int):
            loantime = int(request.json["loantime"])
        else:
            loantime = 28

        if "renewlimit" in request.json and isinstance(request.json["renewlimit"], int):
            renewlimit = int(request.json["renewlimit"])
        else:
            renewlimit = 10

        item = Item(
            barcode=barcode,
            title=title,
            author=author,
            pubyear=pubyear,
            format=format,
            description=description,
            catdate=datetime.now(),
            loantime=loantime,
            renewlimit=renewlimit
        )

        db.session.add(item)
        db.session.commit()
        return "", 201

    except Exception as e:
        return str(e), 409

@app.route("/items/", methods=["GET"])
def get_items():
    if request.method != "GET":
        return "GET method required", 405

    items = Item.query.all()
    
    itemList = []

    for item in items:
        itemInfo = {}
        itemInfo['barcode'] = item.barcode
        itemInfo['title'] = item.title
        itemInfo['author'] = item.author
        itemInfo['pubyear'] = item.pubyear
        itemInfo['format'] = item.format
        itemInfo['description'] = item.description
        itemInfo['catdate'] = item.catdate
        itemInfo['loantime'] = item.loantime
        itemInfo['renewlimit'] = item.renewlimit
        itemList.append(itemInfo)

    return json.dumps(itemList, indent=4, default=str), 200

@app.route("/loans/", methods=["GET"])
def get_loans():
    if request.method != "GET":
        return "GET method required", 405

    loans = Loan.query.all()
    
    loanList = []

    for loan in loans:
        loanInfo = {}
        loanInfo['id'] = loan.id
        loanInfo['item_id'] = loan.item_id
        loanInfo['patron_id'] = loan.patron_id
        loanInfo['loandate'] = loan.loandate
        loanInfo['renewaldate'] = loan.renewaldate
        loanInfo['duedate'] = loan.duedate
        loanInfo['renewed'] = loan.renewed
        loanInfo['status'] = loan.status
        loanList.append(loanInfo)

    return json.dumps(loanList, indent=4, default=str), 200


@app.route("/holds/", methods=["GET"])
def get_holds():
    if request.method != "GET":
        return "GET method required", 405

    holds = Hold.query.all()
    
    holdList = []

    for hold in holds:
        holdInfo = {}
        holdInfo['id'] = hold.id
        holdInfo['item_id'] = hold.item_id
        holdInfo['patron_id'] = hold.patron_id
        holdInfo['holddate'] = hold.holddate
        holdInfo['expirationdate'] = hold.expirationdate
        holdInfo['pickupdate'] = hold.pickupdate
        holdInfo['status'] = hold.status
        holdList.append(holdInfo)

    return json.dumps(holdList, indent=4, default=str), 200