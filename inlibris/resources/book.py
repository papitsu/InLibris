from flask import Response, request, url_for
from flask_restful import Resource
from datetime import datetime
import json
from jsonschema import validate, ValidationError

from inlibris.models import Book
from inlibris.utils import LibraryBuilder, create_error_response
from inlibris.constants import *
from inlibris import db

class BookItem(Resource):
    def get(self, book_id):
        book = Book.query.filter_by(id=book_id).first()
        if book is None:
            return create_error_response(404, "Not found", 
                "No book was found with the id {}".format(book_id)
            )

        body = LibraryBuilder(
            id=book.id,
            barcode=book.barcode,
            title=book.title,
            author=book.author,
            pubyear=book.pubyear,
            format=book.format,
            description=book.description,
            loantime=book.loantime,
            renewlimit=book.renewlimit
        )

        body.add_namespace("inlibris", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.bookitem", book_id=book.id))
        body.add_control("profile", BOOK_PROFILE)
        body.add_control("collection", url_for("api.bookcollection"))
        body.add_control_holds_on(book_id)
        body.add_control_loan_of(book_id)
        body.add_control_edit_book(book_id)
        body.add_control_delete_book(book_id)
        
        return Response(json.dumps(body), 200, mimetype=MASON)

    def put(self, book_id):
        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, LibraryBuilder.book_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        if not Book.query.filter_by(id=book_id).all():
            return create_error_response(404,
                "Book not found",
                None
            )

        if (Book.query.filter_by(barcode=request.json["barcode"]).all()
            and int(Book.query.filter_by(barcode=request.json["barcode"]).first().id) != int(book_id)):
            return create_error_response(409,
                "Barcode reserved",
                "Another book already has a barcode '{}'".format(request.json["barcode"])
            )

        book = Book.query.filter_by(id=book_id).first()

        db.session.delete(book)
        db.session.commit()

        book = Book(
            id=book_id,
            **request.json
        )

        db.session.add(book)
        db.session.commit()

        return Response(status=204)

    def delete(self, book_id):
        if not Book.query.filter_by(id=book_id).all():
            return create_error_response(404,
                "Book not found",
                None
            )
        
        book = Book.query.filter_by(id=book_id).first()
        db.session.delete(book)
        db.session.commit()

        return Response(status=204)

class BookCollection(Resource):
    def get(self):
        body = LibraryBuilder(items=[])
        books = Book.query.all()
        print(len(books))

        for book in books:
            item = LibraryBuilder(
                id=book.id,
                barcode=book.barcode,
                title=book.title,
                author=book.author,
                pubyear=book.pubyear,
                format=book.format,
                description=book.description,
                loantime=book.loantime,
                renewlimit=book.renewlimit
            )

            item.add_control("self", url_for("api.bookitem", book_id=book.id))
            item.add_control("profile", BOOK_PROFILE)
            body["items"].append(item)

        body.add_namespace("inlibris", LINK_RELATIONS_URL + "#")
        body.add_control("self", url_for("api.bookcollection"))
        body.add_control("profile", BOOK_PROFILE)
        body.add_control_all_patrons()
        body.add_control_add_book()

        return Response(json.dumps(body), 200, mimetype=MASON)

    def post(self):

        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, LibraryBuilder.book_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        if (Book.query.filter_by(barcode=request.json["barcode"]).all()):
            return create_error_response(409,
                "Already exists",
                "Barcode '{}' already exists on another book.".format(request.json["barcode"])
            )
    
        book = Book(
            **request.json
        )

        db.session.add(book)
        db.session.commit()
        
        headerDictionary = {}
        headerDictionary['Location'] = url_for("api.bookitem", book_id=Book.query.filter_by(barcode=request.json["barcode"]).first().id)
        
        return Response(status=201, headers=headerDictionary)