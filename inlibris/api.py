import json
from flask import Blueprint, request, Response
from flask_restful import Resource, Api
from inlibris.constants import *
from inlibris.utils import LibraryBuilder

api_bp = Blueprint("api", __name__, url_prefix="/api")
api = Api(api_bp)

from inlibris.resources.patron import PatronItem, PatronCollection
from inlibris.resources.book import BookItem, BookCollection
from inlibris.resources.loan import LoanItem, LoansByPatron

api.add_resource(PatronCollection, "/patrons/")
api.add_resource(PatronItem, "/patrons/<patron_id>/")

api.add_resource(BookCollection, "/books/")
api.add_resource(BookItem, "/books/<book_id>/")

api.add_resource(LoansByPatron, "/patrons/<patron_id>/loans/")
api.add_resource(LoanItem, "/books/<book_id>/loan")

@api_bp.route("/")
def api_entrypoint():
    body = LibraryBuilder()
    body.add_namespace("inlibris", LINK_RELATIONS_URL + "#")
    body.add_control_all_patrons()
    body.add_control_all_books()
    return Response(json.dumps(body), 200, mimetype=MASON)
