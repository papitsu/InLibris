from flask import Response, request, url_for
from flask_restful import Resource
from datetime import datetime, timedelta
import json
from jsonschema import validate, ValidationError

from inlibris.models import Loan, Book, Patron, Hold
from inlibris.utils import LibraryBuilder, create_error_response, date_converter
from inlibris.constants import *
from inlibris import db

class HoldItem(Resource):
    pass
#    def get(self, patron_id, hold_id):
#        return Response("Placeholder get hold item", status=200, mimetype=MASON)
    '''
    def put(self, patron_id, hold_id):
                if not request.json:
                    return create_error_response(415,
                        "Unsupported media type",
                        "Requests must be JSON"
                    )
        return Response("Placeholder put hold item", status=200, mimetype=MASON)


    def delete(self, patron_id, hold_id):
        return Response("Placeholder put hold item", status=204, mimetype=MASON)
    '''
class HoldsOnBook(Resource):
    def get(self, book_id):
        return Response("Placeholder HoldsOnBook", status=200, mimetype=MASON)


class HoldsByPatron(Resource):
    pass
    #def get(self, patron_id):
    #    return Response("Placeholder Get HoldsByPatron", status=200, mimetype=MASON)
    '''
    def post(self, patron_id):

                if not request.json:
                    return create_error_response(415,
                        "Unsupported media type",
                        "Requests must be JSON"
                    )

        return Response("Placeholder Post HoldsByPatron", status=201, mimetype=MASON)
    '''



