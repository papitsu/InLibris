from datetime import datetime, timedelta
import json
from jsonschema import validate

from flask_restful import Resource, Api
from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy

from inlibris.models import Patron, Book, Hold, Loan
from inlibris.constants import *

def _populate_db(db):
    patron1 = Patron(
        barcode=100001,
        firstname="Hilma",
        lastname="Kirjastontäti",
        email="hilma@kirjasto.fi",
        group="Staff",
        status="Active",
        regdate=datetime(2020,1,1)
    )

    patron2 = Patron(
        barcode=100002,
        firstname="Testi",
        lastname="Käyttäjä",
        email="kayttaja@test.com",
        regdate=datetime(1999,12,31)
    )

    item1 = Book(
        barcode=200001,
        title="Garpin maailma",
        author="Irving, John",
        pubyear=2011,
        format="book",
        description="ISBN 978-951-31-1264-6"
    )

    item2 = Book(
        barcode=200002,
        title="Minä olen monta",
        author="Irving, John",
        pubyear=2013,
        format="book",
        description="ISBN 978-951-31-7092-9"
    )

    item3 = Book(
        barcode=200003,
        title="Oman elämänsä sankari",
        author="Irving, John",
        pubyear=2009,
        format="book",
        description="ISBN 978-951-31-6307-8"
    )

    loan1 = Loan(
        book=item1,
        patron=patron2,
        loandate=datetime(2020,4,2).date(),
        duedate=(datetime(2020,4,2) + timedelta(days=28)).date()
    )

    loan2 = Loan(
        book=item3,
        patron=patron2,
        loandate=datetime(2020,4,2).date(),
        duedate=(datetime(2020,4,2) + timedelta(days=28)).date()
    )

    hold1 = Hold(
        book=item1,
        patron=patron1,
        holddate=datetime(2020,4,2).date(),
        expirationdate=(datetime(2020,4,2) + timedelta(days=45)).date()
    )

    hold2 = Hold(
        book=item3,
        patron=patron1,
        holddate=datetime(2020,4,2).date(),
        expirationdate=(datetime(2020,4,2) + timedelta(days=45)).date()
    )

    db.session.add(patron1)
    db.session.add(patron2)
    db.session.add(item1)
    db.session.add(item2)
    db.session.add(item3)
    db.session.add(loan1)
    db.session.add(loan2)
    db.session.add(hold1)
    db.session.add(hold2)
    db.session.commit()

def _get_patron_json(barcode=123456, email="test@test.com", firstname="Testi"):
    """
    Creates a valid patron JSON object to be used for PUT and POST tests.
    """
    
    return {"barcode": barcode, "firstname": firstname, "email": email}

def _get_book_json(barcode=234567, pubyear=2020):
    """
    Creates a valid book JSON object to be used for PUT and POST tests.
    """
    
    return {"barcode": barcode, "title": "Testikirja", "pubyear": pubyear}

def _get_add_loan_json(book_barcode=200002):
    """
    Creates a valid loan JSON object to be used for POST tests.
    """
    
    return {"book_barcode": book_barcode}

def _get_edit_loan_json(book_barcode=200001, patron_barcode=100002):
    """
    Creates a valid loan JSON object to be used for PUT tests.
    """
    
    return {
        "patron_barcode": patron_barcode,
        "loandate": "2020-03-03",
        "renewaldate": "2020-03-04",
        "duedate": "2020-04-02",
        "renewed": 1,
        "status": "Renewed",
    }

def _check_namespace(client, response):
    """
    Checks that the "inlibris" namespace is found from the response body, and
    that its "name" attribute is a URL that can be accessed.
    """
    
    ns_href = response["@namespaces"]["inlibris"]["name"]
    resp = client.get(ns_href)
    assert resp.status_code == 200

def _check_control_get_method(ctrl, client, obj):
    """
    Checks a GET type control from a JSON object be it root document or an item
    in a collection. Also checks that the URL of the control can be accessed.
    """
    
    href = obj["@controls"][ctrl]["href"]
    resp = client.get(href)
    assert resp.status_code == 200

def _check_control_delete_method(ctrl, client, obj):
    """
    Checks a DELETE type control from a JSON object be it root document or an
    item in a collection. Checks the contrl's method in addition to its "href".
    Also checks that using the control results in the correct status code of 204.
    """
    
    href = obj["@controls"][ctrl]["href"]
    method = obj["@controls"][ctrl]["method"].lower()
    assert method == "delete"
    resp = client.delete(href)
    assert resp.status_code == 204

def _check_control_put_patron_method(ctrl, client, obj):
    """
    Checks a PUT type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid sensor against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 204.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "put"
    assert encoding == "json"
    body = _get_patron_json()
    body["barcode"] = obj["barcode"]
    body["firstname"] = obj["firstname"]
    body["email"] = obj["email"]
    validate(body, schema)
    resp = client.put(href, json=body)
    assert resp.status_code == 204

def _check_control_put_book_method(ctrl, client, obj):
    """
    Checks a PUT type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid sensor against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 204.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "put"
    assert encoding == "json"
    body = _get_book_json()
    body["barcode"] = obj["barcode"]
    validate(body, schema)
    resp = client.put(href, json=body)
    assert resp.status_code == 204

def _check_control_put_loan_method(ctrl, client, obj):
    """
    Checks a PUT type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid sensor against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 204.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "put"
    assert encoding == "json"
    body = _get_edit_loan_json()
    body["book_barcode"] = obj["book_barcode"]
    body["patron_barcode"] = obj["patron_barcode"]
    validate(body, schema)
    resp = client.put(href, json=body)
    assert resp.status_code == 200

def _check_control_post_patron_method(ctrl, client, obj):
    """
    Checks a POST type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid sensor against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 201.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "post"
    assert encoding == "json"
    body = _get_patron_json()
    validate(body, schema)
    resp = client.post(href, json=body)
    assert resp.status_code == 201

def _check_control_post_book_method(ctrl, client, obj):
    """
    Checks a POST type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid sensor against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 201.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "post"
    assert encoding == "json"
    body = _get_book_json()
    validate(body, schema)
    resp = client.post(href, json=body)
    assert resp.status_code == 201

def _check_control_post_loan_method(ctrl, client, obj):
    """
    Checks a POST type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid sensor against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 201.
    """
    
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "post"
    assert encoding == "json"
    body = _get_add_loan_json()
    validate(body, schema)
    resp = client.post(href, json=body)
    assert resp.status_code == 201