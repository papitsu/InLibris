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
    barcode = db.Column(db.String(6), unique=True, nullable=False, primary_key=True)
    firstname = db.Column(db.String(64), nullable=False)
    lastname = db.Column(db.String(64), default=None)
    email = db.Column(db.String(64), unique=True, nullable=False)
    group = db.Column(db.String(64), nullable=False, default="Customer")
    status = db.Column(db.String(64), nullable=False, default="Active")
    regdate = db.Column(db.DateTime, nullable=False)
    
    loan = db.relationship("Loan", back_populates="patron")
    hold = db.relationship("Hold", back_populates="patron")

class Item(db.Model):
    barcode = db.Column(db.String(6), unique=True, nullable=False, primary_key=True)
    title = db.Column(db.String(64), nullable=False)
    author = db.Column(db.String(64))
    publisher = db.Column(db.String(64))
    pubyear = db.Column(db.String(4), nullable=False)
    format = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(512), nullable=False)
    catdate = db.Column(db.DateTime, nullable=False)
    loantime = db.Column(db.Integer, nullable=False, default=28)
    renewals = db.Column(db.Integer, nullable=False, default=10)
    
    loan = db.relationship("Loan", back_populates="item")
    hold = db.relationship("Hold", back_populates="item")

class Loan(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    item_barcode = db.Column(db.String(6), db.ForeignKey("item.barcode"), nullable=False, unique=True)
    patron_barcode = db.Column(db.String(6), db.ForeignKey("patron.barcode"), nullable=False)
    loandate = db.Column(db.DateTime, nullable=False)
    renewaldate = db.Column(db.DateTime, default=None)
    duedate = db.Column(db.DateTime, nullable=False)
    renewed = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(64), default="Charged", nullable=False)
    
    item = db.relationship("Item", back_populates="loan")
    patron = db.relationship("Patron", back_populates="loan")

class Hold(db.Model):
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    item_barcode = db.Column(db.String(6), db.ForeignKey("item.barcode"), nullable=False)
    patron_barcode = db.Column(db.String(6), db.ForeignKey("patron.barcode"), nullable=False)
    holddate = db.Column(db.DateTime, nullable=False)
    expirationdate = db.Column(db.DateTime, nullable=False)
    pickupdate = db.Column(db.DateTime, default=None)
    renewed = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(64), default="Requested", nullable=False)
    
    item = db.relationship("Item", back_populates="hold")
    patron = db.relationship("Patron", back_populates="hold")

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

        if "publisher" in request.json and isinstance(request.json["publisher"], str):
            publisher = request.json["publisher"]
        else:
            publisher = None

        if "format" in request.json and isinstance(request.json["format"], str):
            format = request.json["format"]
        else:
            format = "book"

        if "description" in request.json and isinstance(request.json["description"], str):
            description = request.json["description"]
        else:
            description = None

        if "loantime" in request.json and isinstance(request.json["loantime"], int):
            loantime = int(request.json["loantime"])
        else:
            loantime = 28

        if "renewals" in request.json and isinstance(request.json["renewals"], int):
            renewals = int(request.json["renewals"])
        else:
            renewals = 10

        item = Item(
            barcode=barcode,
            title=title,
            author=author,
            publisher=publisher,
            pubyear=pubyear,
            format=format,
            description=description,
            catdate=datetime.now(),
            loantime=loantime,
            renewals=renewals
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
        itemInfo['publisher'] = item.publisher
        itemInfo['pubyear'] = item.pubyear
        itemInfo['format'] = item.format
        itemInfo['description'] = item.description
        itemInfo['catdate'] = item.catdate
        itemInfo['loantime'] = item.loantime
        itemInfo['renewals'] = item.renewals
        itemList.append(itemInfo)

    return json.dumps(itemList, indent=4, default=str), 200