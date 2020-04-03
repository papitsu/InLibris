from datetime import datetime, timedelta
import json

from flask_restful import Resource, Api
from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy

from inlibris.models import Patron, Book, Hold, Loan
from inlibris.constants import *
from . import api

'''
# Needed this in development, don't need it now
# Still keeping it here in case I need it again

def without_keys(d, keys):
    """
    Return a copy of a dictionary "d" excluding keys specified in list "keys".
    
    Source: https://stackoverflow.com/a/31434038
    """
    
    return {x: d[x] for x in d if x not in keys}
'''

def date_converter(date_str):
    """
    Convert a date string "YYYY-MM-DD" to datetime object.
    """

    return datetime.strptime(date_str, "%Y-%m-%d").date()

class MasonBuilder(dict):
    """
    A convenience class for managing dictionaries that represent Mason
    objects. It provides nice shorthands for inserting some of the more
    elements into the object but mostly is just a parent for the much more
    useful subclass defined next. This class is generic in the sense that it
    does not contain any application specific implementation details.

    Taken straight from course material:
    https://lovelace.oulu.fi/ohjelmoitava-web/programmable-web-project-spring-2020/implementing-rest-apis-with-flask/
    """

    def add_error(self, title, details):
        """
        Adds an error element to the object. Should only be used for the root
        object, and only in error scenarios.

        Note: Mason allows more than one string in the @messages property (it's
        in fact an array). However we are being lazy and supporting just one
        message.

        : param str title: Short title for the error
        : param str details: Longer human-readable description
        """

        self["@error"] = {
            "@message": title,
            "@messages": [details],
        }

    def add_namespace(self, ns, uri):
        """
        Adds a namespace element to the object. A namespace defines where our
        link relations are coming from. The URI can be an address where
        developers can find information about our link relations.

        : param str ns: the namespace prefix
        : param str uri: the identifier URI of the namespace
        """

        if "@namespaces" not in self:
            self["@namespaces"] = {}

        self["@namespaces"][ns] = {
            "name": uri
        }

    def add_control(self, ctrl_name, href, **kwargs):
        """
        Adds a control property to an object. Also adds the @controls property
        if it doesn't exist on the object yet. Technically only certain
        properties are allowed for kwargs but again we're being lazy and don't
        perform any checking.

        The allowed properties can be found from here
        https://github.com/JornWildt/Mason/blob/master/Documentation/Mason-draft-2.md

        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        """

        if "@controls" not in self:
            self["@controls"] = {}

        self["@controls"][ctrl_name] = kwargs
        self["@controls"][ctrl_name]["href"] = href

class LibraryBuilder(MasonBuilder):
    """
    An application specific subclass for MasonBuilder to manage adding
    hypermedia controls to json documents.
    """

    @staticmethod
    def patron_schema():
        print(api.api_bp.static_folder + '/schema/patron.json')
        with open(api.api_bp.static_folder + '/schema/patron.json', 'r') as f:
            schema = json.load(f)

        return schema

    @staticmethod
    def book_schema():
        with open(api.api_bp.static_folder + '/schema/book.json', 'r') as f:
            schema = json.load(f)

        return schema

    @staticmethod
    def edit_loan_schema():
        with open(api.api_bp.static_folder + '/schema/edit_loan.json', 'r') as f:
            schema = json.load(f)

        return schema

    @staticmethod
    def add_loan_schema():
        with open(api.api_bp.static_folder + '/schema/add_loan.json', 'r') as f:
            schema = json.load(f)

        return schema

    '''
    # Commented out due to holds not being implemented
    @staticmethod
    def edit_hold_schema():    
        schema = {
            "type": "object",
            "required": ["book_barcode", "patron_barcode", "holddate", "expirationdate"]
        }
        props = schema["properties"] = {}
        props["book_barcode"] = {
            "description": "Book's unique barcode",
            "type": "integer",
            "minimum": 200000,
            "maximum": 299999
        }
        props["patron_barcode"] = {
            "description": "Patron's unique barcode",
            "type": "integer",
            "minimum": 100000,
            "maximum": 199999
        }
        props["holddate"] = {
            "description": "Date when hold was created",
            "type": "string",
            "format": "date"
        }
        props["expirationdate"] = {
            "description": "Date when hold will expire",
            "type": "string",
            "format": "date"
        }
        props["pickupdate"] = {
            "description": "Date when hold must be picked up",
            "type": "string",
            "format": "date"
        }
        props["status"] = {
            "description": "The hold's status",
            "type": "string",
            "default": "Requested",
            "enum": ["Requested", "On hold"]
        }
        return schema
    '''

    '''
    # Commented out due to holds not being implemented
    @staticmethod
    def add_hold_schema():    
        schema = {
            "type": "object",
            "required": ["book_barcode"]
        }
        props = schema["properties"] = {}
        props["book_barcode"] = {
            "description": "Book's unique barcode",
            "type": "integer",
            "minimum": 200000,
            "maximum": 299999
        }
        props["expirationdate"] = {
            "description": "Hold's expiration date",
            "type": "string",
            "format": "date"
        }
        return schema
    '''

    def add_control_all_patrons(self):
        self.add_control(
            "inlibris:patrons-all",
            "/inlibris/api/patrons/",
            method="GET",
            title="Get all patrons"
        )

    def add_control_all_books(self):
        self.add_control(
            "inlibris:books-all",
            "/inlibris/api/books/",
            method="GET",
            title="Get all books"
        )

    def add_control_delete_patron(self, patron_id):
        self.add_control(
            "inlibris:delete",
            "/inlibris/api/patrons/%s/" % patron_id,
            method="DELETE",
            title="Delete this patron"
        )

    def add_control_delete_book(self, book_id):
        self.add_control(
            "inlibris:delete",
            "/inlibris/api/books/%s/" % book_id,
            method="DELETE",
            title="Delete this book"
        )

    def add_control_delete_loan(self, book_id):
        self.add_control(
            "inlibris:delete",
            "/inlibris/api/books/%s/loan/" % book_id,
            method="DELETE",
            title="Delete this loan"
        )

    '''
    # Commented out due to holds not being implemented
    def add_control_delete_hold(self, patron_id, hold_id):
        self.add_control(
            "inlibris:delete",
            "/inlibris/api/patrons/{}/holds/{}/".format(patron_id, hold_id),
            method="DELETE",
            title="Delete this hold"
        )
    '''

    def add_control_add_patron(self):
        self.add_control(
            "inlibris:add-patron",
            "/inlibris/api/patrons/",
            method="POST",
            encoding="json",
            title="Add a patron",
            schema=self.patron_schema()
        )
        
    def add_control_edit_patron(self, patron_id):
        self.add_control(
            "edit",
            "/inlibris/api/patrons/%s/" % patron_id,
            title="Edit this patron",
            encoding="json",
            method="PUT",
            schema=self.patron_schema()
        )

    def add_control_add_book(self):
        self.add_control(
            "inlibris:add-book",
            "/inlibris/api/books/",
            method="POST",
            encoding="json",
            title="Add a book",
            schema=self.book_schema()
        )

    def add_control_edit_book(self, book_id):
        self.add_control(
            "edit",
            "/inlibris/api/books/%s/" % book_id,
            title="Edit this book",
            encoding="json",
            method="PUT",
            schema=self.book_schema()
        )

    def add_control_loans_by(self, patron_id):
        self.add_control(
            "inlibris:loans-by",
            "/inlibris/api/patrons/%s/loans/" % patron_id,
            title="Loans by patron",
            method="GET"
        )

    def add_control_add_loan(self, patron_id):
        self.add_control(
            "inlibris:add-loan",
            "/inlibris/api/patrons/%s/loans/" % patron_id,
            method="POST",
            encoding="json",
            title="Add a new loan to this patron",
            schema=self.add_loan_schema()
        )

    def add_control_edit_loan(self, book_id):
        self.add_control(
            "edit",
            "/inlibris/api/books/%s/loan/" % book_id,
            title="Edit this loan",
            encoding="json",
            method="PUT",
            schema=self.edit_loan_schema()
        )

    def add_control_holds_by(self, patron_id):
        self.add_control(
            "inlibris:holds-by",
            "/inlibris/api/patrons/%s/holds/" % patron_id,
            title="Holds by patron",
            method="GET"
        )

    def add_control_loan_of(self, book_id):
        self.add_control(
            "inlibris:loan-of",
            "/inlibris/api/books/%s/loan/" % book_id,
            title="Loan of book",
            method="GET"
        )

    def add_control_holds_on(self, book_id):
        self.add_control(
            "inlibris:holds-on",
            "/inlibris/api/books/%s/holds/" % book_id,
            title="Holds on book",
            method="GET"
        )

    def add_control_target_book(self, book_id):
        self.add_control(
            "inlibris:target-book",
            "/inlibris/api/books/%s/" % book_id,
            title="Target book",
            method="GET"
        )

def create_error_response(status_code, title, message=None):
    """
    An HTTP error response in MASON hypermedia format.

    Taken straight from course material:
    https://lovelace.oulu.fi/ohjelmoitava-web/programmable-web-project-spring-2020/implementing-rest-apis-with-flask/
    """
    resource_url = request.path
    body = MasonBuilder(resource_url=resource_url)
    body.add_error(title, message)
    body.add_control("profile", href=ERROR_PROFILE)
    return Response(json.dumps(body), status_code, mimetype=MASON)