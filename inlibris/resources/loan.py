from flask import Response, request, url_for
from flask_restful import Resource
from datetime import datetime, timedelta
import json
from jsonschema import validate, ValidationError

from inlibris.models import Loan, Book, Patron
from inlibris.utils import LibraryBuilder, create_error_response, date_converter
from inlibris.constants import *
from inlibris import db

class LoanItem(Resource):
    '''
    HTTP method implementations for the LoanItem resource. Supports GET, PUT and DELETE.
    '''

    def get(self, book_id):
        '''
        Gets the information for a single loan.

        Input: book_id
        Output HTTP responses:
            200 (when book_id is valid)
            400 (when book_id is valid but book is not loaned)
            404 (when book_id is invalid)
        '''

        book = Book.query.filter_by(id=book_id).first()
        if book is None:
            return create_error_response(404,
                "Book not found", 
                None
            )

        loan = Loan.query.filter_by(book_id=book_id).first()
        if loan is None:
            return create_error_response(400, "Book not loaned", None)

        book_barcode = Book.query.filter_by(id=book_id).first().barcode
        patron_barcode = Patron.query.filter_by(id=loan.patron_id).first().barcode

        body = LibraryBuilder(
            id=loan.id,
            book_barcode=book_barcode,
            patron_barcode=patron_barcode,
            loandate=str(loan.loandate.date()),
            renewaldate=None if not loan.renewaldate else str(loan.renewaldate.date()),
            duedate=str(loan.duedate.date()),
            renewed=loan.renewed,
            status=loan.status
        )

        body.add_namespace("inlibris", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.loanitem", book_id=book_id))
        body.add_control("profile", LOAN_PROFILE)
        body.add_control("author", url_for("api.patronitem", patron_id=loan.patron_id))
        body.add_control_loans_by(loan.patron_id)
        body.add_control_target_book(book_id)
        body.add_control_all_books()
        body.add_control_all_patrons()
        body.add_control_edit_loan(book_id)
        body.add_control_delete_loan(book_id)
        
        return Response(json.dumps(body), 200, mimetype=MASON)

    def put(self, book_id):
        '''
        Edit a loan (e.g. renew)

        Input: book_id in URI and a JSON document as HTTP request body.
        Output HTTP responses:
            200 (when loan information was updated succesfully)
            204 (when book_id is valid but book is not on loan)
            400 (when JSON document didn't validate against the schema)
            404 (when book_id is invalid or patron barcode in request body is invalid)
            415 (when HTTP request body is not JSON)
        '''

        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, LibraryBuilder.edit_loan_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        book = Book.query.filter_by(id=book_id).first()
        patron = Patron.query.filter_by(barcode=request.json["patron_barcode"]).first()

        if patron is None:
            return create_error_response(404,
                "Patron not found", 
                None
            )

        if book is None:
            return create_error_response(404,
                "Book not found", 
                None
            )
                
        loan = Loan.query.filter_by(book_id=book_id).first()
        if loan is None:
            return Response(status=204)

        # TODO: Check more errors: what if they try to change book_id to a book that is already
        # on loan or something like that?

        db.session.delete(loan)
        db.session.commit()

        if "renewaldate" in request.json:
            renewaldate = date_converter(request.json["renewaldate"])
        else:
            renewaldate = None

        if "renewed" in request.json:
            renewed = request.json["renewed"]
        else:
            renewed = 0           

        if "status" in request.json:
            status = request.json["status"]
        else:
            status = "Charged"

        loan = Loan(
            patron_id = patron.id,
            book_id = book_id,
            duedate = date_converter(request.json["duedate"]),
            renewaldate = renewaldate,
            loandate = date_converter(request.json["loandate"]),
            renewed = renewed,
            status = status
        )

        db.session.add(loan)
        db.session.commit()

        return Response(status=200)

    def delete(self, book_id):
        '''
        Delete a loan from the database

        Input: book_id
        Output HTTP responses:
            204 (when loan was deleted succesfully or the book is not loaned)
            404 (when book_id is invalid)
        '''

        book = Book.query.filter_by(id=book_id).first()
        if book is None:
            return create_error_response(404,
                "Book not found", 
                None
            )

        loan = Loan.query.filter_by(book_id=book_id).first()

        if not loan:
            return Response(status=204)

        db.session.delete(loan)
        db.session.commit()

        return Response(status=204)

class LoansByPatron(Resource):
    '''
    HTTP method implementations for the LoansByPatron resource. Supports GET and POST.
    '''

    def get(self, patron_id):
        '''
        Get the info for all the loans by a patron.

        Input: patron_id
        Output HTTP responses:
            200 (patron_id is valid)
            404 (patron_id is invalid)
        '''

        patron = Patron.query.filter_by(id=patron_id).first()

        if patron is None:
            return create_error_response(404,
                "Patron not found", 
                None
            )

        loans = Loan.query.filter_by(patron_id=patron_id).all()
        body = LibraryBuilder(items=[])

        for loan in loans:
            book_barcode = Book.query.filter_by(id=loan.book_id).first().barcode
            patron_barcode = Patron.query.filter_by(id=patron_id).first().barcode

            item = LibraryBuilder(
                id=loan.id,
                book_barcode=book_barcode,
                patron_barcode=patron_barcode,
                loandate=str(loan.loandate.date()),
                renewaldate=None if not loan.renewaldate else str(loan.renewaldate.date()),
                duedate=str(loan.duedate.date()),
                renewed=loan.renewed,
                status=loan.status
            )

            item.add_control("self", url_for("api.loanitem", book_id=loan.book_id))
            item.add_control("profile", LOAN_PROFILE)
            body["items"].append(item)

        body.add_namespace("inlibris", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.loansbypatron", patron_id=patron_id))
        body.add_control("author", url_for("api.patronitem", patron_id=patron_id))
        body.add_control("profile", LOAN_PROFILE)
        body.add_control_all_patrons()
        body.add_control_all_books()
        body.add_control_add_loan(patron_id)

        return Response(json.dumps(body), 200, mimetype=MASON)


    def post(self, patron_id):
        '''
        Add a loan by a patron.

        Input: patron_id in URI and JSON document as HTTP request body.
        Output HTTP responses:
            201 (when loan was added succesfully)
            400 (when JSON document didn't validate against the schema)
            404 (when the patron_id is invalid or book_barcode in the request body is invalid)
            409 (when the book is already loaned)
            415 (when HTTP request body is not JSON)
        '''

        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, LibraryBuilder.add_loan_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        book = Book.query.filter_by(barcode=request.json["book_barcode"]).first()
        patron = Patron.query.filter_by(id=patron_id).first()

        if patron is None:
            return create_error_response(404,
                "Patron not found", 
                None
            )

        if book is None:
            return create_error_response(404,
                "Book not found", 
                None
            )

        conflict_loan = Loan.query.filter_by(book_id=book.id).first()

        if conflict_loan:
            conflict_patron = Patron.query.filter_by(id=conflict_loan.patron_id).first()
            return create_error_response(409,
                "Already exists",
                "Patron '{}' already has loan with book '{}'"
                .format(conflict_patron.barcode, book.barcode)
            )
    
        if "duedate" in request.json:
            duedate = date_converter(request.json["duedate"])
        else:
            duedate = datetime.now() + timedelta(days=book.loantime)

        loan = Loan(
            patron_id=patron_id,
            book_id=book.id,
            loandate=datetime.now().date(),
            duedate=duedate
        )

        db.session.add(loan)
        db.session.commit()
        
        headerDictionary = {}
        headerDictionary['Location'] = url_for("api.loanitem", book_id=Book.query.filter_by(barcode=request.json["book_barcode"]).first().id)
        
        return Response(status=201, headers=headerDictionary)