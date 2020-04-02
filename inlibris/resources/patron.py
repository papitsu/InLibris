from flask import Response, request, url_for
from flask_restful import Resource
from datetime import datetime
import json
from jsonschema import validate, ValidationError

from inlibris.models import Patron
from inlibris.utils import LibraryBuilder, create_error_response
from inlibris.constants import *
from inlibris import db

class PatronItem(Resource):
    def get(self, patron_id):
        patron = Patron.query.filter_by(id=patron_id).first()
        if patron is None:
            return create_error_response(404, "Not found", 
                "No patron was found with the id {}".format(patron_id)
            )

        body = LibraryBuilder(
            id=patron.id,
            barcode=patron.barcode,
            firstname=patron.firstname,
            lastname=patron.lastname,
            email=patron.email,
            group=patron.group,
            status=patron.status,
            regdate=str(patron.regdate.date())
        )

        body.add_namespace("inlibris", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.patronitem", patron_id=patron.id))
        body.add_control("profile", PATRON_PROFILE)
        body.add_control_loans_by(patron_id)
        body.add_control_holds_by(patron_id)
        body.add_control("collection", url_for("api.patroncollection"))
        body.add_control_edit_patron(patron_id)
        body.add_control_delete_patron(patron_id)
        
        return Response(json.dumps(body), 200, mimetype=MASON)

    def put(self, patron_id):
        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, LibraryBuilder.patron_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        if (Patron.query.filter_by(barcode=request.json["barcode"]).all()
            and int(Patron.query.filter_by(barcode=request.json["barcode"]).first().id) != int(patron_id)):
            return create_error_response(409,
                "Patron barcode reserved",
                "Another patron already has a barcode '{}'".format(request.json["barcode"])
            )
        
        if not Patron.query.filter_by(id=patron_id).all():
            return create_error_response(404,
                "Not found",
                "Patron does not exist"
            )

        patron = Patron.query.filter_by(id=patron_id).first()
        regdate = patron.regdate

        db.session.delete(patron)
        db.session.commit()

        patron = Patron(
            id=patron_id,
            regdate=regdate,
            **request.json
        )

        db.session.add(patron)
        db.session.commit()

        return Response(status=204) 

    def delete(self, patron_id):
        if not Patron.query.filter_by(id=patron_id).all():
            return create_error_response(404,
                "Patron not found",
                None
            )
        
        patron = Patron.query.filter_by(id=patron_id).first()
        db.session.delete(patron)
        db.session.commit()

        return Response(status=204)

class PatronCollection(Resource):
    def get(self):
        body = LibraryBuilder(items=[])
        patrons = Patron.query.all()
        print(len(patrons))

        for patron in patrons:
            item = LibraryBuilder(
                id=patron.id,
                barcode=patron.barcode,
                firstname=patron.firstname,
                lastname=patron.lastname,
                email=patron.email,
                group=patron.group,
                status=patron.status,
                regdate=str(patron.regdate.date())
            )
            item.add_control("self", url_for("api.patronitem", patron_id=patron.id))
            item.add_control("profile", PATRON_PROFILE)
            body["items"].append(item)

        body.add_namespace("inlibris", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.patroncollection"))
        body.add_control("profile", PATRON_PROFILE)
        body.add_control_add_patron()
        body.add_control_all_books()

        return Response(json.dumps(body), 200, mimetype=MASON)

    def post(self):

        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, LibraryBuilder.patron_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        if (Patron.query.filter_by(barcode=request.json["barcode"]).all()):
            return create_error_response(409,
                "Already exists",
                "There is already a patron with the barcode '{}' in the collection".format(request.json["barcode"])
            )

        if (Patron.query.filter_by(email=request.json["email"]).all()):
            return create_error_response(409,
                "Already exists",
                "There is already a patron with the email '{}' in the collection".format(request.json["email"])
            )
    
        patron = Patron(
            regdate=datetime.now().date(),
            **request.json
        )

        db.session.add(patron)
        db.session.commit()
        
        headerDictionary = {}
        headerDictionary['Location'] = url_for("api.patronitem", patron_id=Patron.query.filter_by(barcode=request.json["barcode"]).first().id)
        
        return Response(status=201, headers=headerDictionary)