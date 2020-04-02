import json
from flask import Blueprint, request, Response, redirect
from flask_restful import Resource, Api
from inlibris.constants import *
from inlibris.utils import LibraryBuilder

root_bp = Blueprint("root", __name__, url_prefix="")
api_bp = Blueprint("api", __name__, url_prefix="/api")
api = Api(api_bp)

from inlibris.resources.patron import PatronItem, PatronCollection
from inlibris.resources.book import BookItem, BookCollection
from inlibris.resources.loan import LoanItem, LoansByPatron
from inlibris.resources.hold import HoldItem, HoldsOnBook, HoldsByPatron

api.add_resource(PatronCollection, "/patrons/")
api.add_resource(PatronItem, "/patrons/<patron_id>/")

api.add_resource(BookCollection, "/books/")
api.add_resource(BookItem, "/books/<book_id>/")

api.add_resource(LoansByPatron, "/patrons/<patron_id>/loans/")
api.add_resource(LoanItem, "/books/<book_id>/loan/")

api.add_resource(HoldsOnBook, "/books/<book_id>/holds/")
api.add_resource(HoldsByPatron, "/patrons/<patron_id>/holds/")
api.add_resource(HoldItem, "/patrons/<patron_id>/holds/<hold_id>/")

@api_bp.route("/")
def api_entrypoint():
    body = LibraryBuilder()
    body.add_namespace("inlibris", LINK_RELATIONS_URL)
    body.add_control_all_patrons()
    body.add_control_all_books()
    return Response(json.dumps(body), 200, mimetype=MASON)

@root_bp.route(LINK_RELATIONS_URL)
def namespace():
    return redirect(APIARY_URL + "link-relations/", 200)

@root_bp.route(PATRON_PROFILE)
@root_bp.route(BOOK_PROFILE)
@root_bp.route(LOAN_PROFILE)
@root_bp.route(HOLD_PROFILE)
@root_bp.route(ERROR_PROFILE)
def profiles():
    return redirect(APIARY_URL + "profiles/", 200)
