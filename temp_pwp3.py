import json
from flask import Flask, Response, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from jsonschema import validate, ValidationError

MASON = "application/vnd.mason+json"
PRODUCT_PROFILE = "/profiles/product/"
STORAGE_PROFILE = "/profiles/storage/"
ERROR_PROFILE = "/profiles/error/"
LINK_RELATIONS_URL = "/storage/link-relations/"
APIARY_URL = "https://yourproject.docs.apiary.io/#reference/"

class MasonBuilder(dict):
    """
    A convenience class for managing dictionaries that represent Mason
    objects. It provides nice shorthands for inserting some of the more
    elements into the object but mostly is just a parent for the much more
    useful subclass defined next. This class is generic in the sense that it
    does not contain any application specific implementation details.
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

class InventoryBuilder(MasonBuilder):

    @staticmethod
    def product_schema():
        schema = {
            "type": "object",
            "required": ["handle", "weight", "price"]
        }
        props = schema["properties"] = {}
        props["handle"] = {
            "description": "Product's unique handle",
            "type": "string"
        }
        props["weight"] = {
            "description": "Weight of product",
            "type": "number"
        }
        props["price"] = {
            "description": "Price of product",
            "type": "number"
        }
        return schema

    def add_control_all_products(self):
        self.add_control(
            "storage:products-all",
            "/api/products/",
            method="GET",
            encoding="json",
            title="Get all products"
        )

    def add_control_delete_product(self, handle):
        self.add_control(
            "storage:delete",
            "/api/products/%s/" % handle,
            method="DELETE",
            encoding="json",
            title="Delete a product"
        )
        
    def add_control_add_product(self):
        self.add_control(
            "storage:add-product",
            "/api/products/",
            method="POST",
            encoding="json",
            title="Add a product",
            schema=self.product_schema()
        )
        
    def add_control_edit_product(self, handle):
        self.add_control(
            "edit",
            "/api/products/%s/" % handle,
            method="PUT",
            encoding="json",
            title="Edit a product",
            schema=self.product_schema()
        )
        
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
api = Api(app)

def create_error_response(status_code, title, message=None):
    resource_url = request.path
    body = MasonBuilder(resource_url=resource_url)
    body.add_error(title, message)
    body.add_control("profile", href=ERROR_PROFILE)
    return Response(json.dumps(body), status_code, mimetype=MASON)

class StorageEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qty = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    location = db.Column(db.String(64), nullable=False)
    
    product = db.relationship("Product", back_populates="in_storage")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(64), unique=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    in_storage = db.relationship("StorageEntry", back_populates="product")
    
class ProductItem(Resource):
    
    def get(self, handle):
        db_product = Product.query.filter_by(handle=handle).first()
        if db_product is None:
            return create_error_response(404, "Not found", 
                "No product was found with the handle {}".format(handle)
            )

        body = InventoryBuilder(
            handle=db_product.handle,
            weight=db_product.weight,
            price=db_product.price
        )

        body.add_namespace("storage", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(ProductItem, handle=handle))
        body.add_control("collection", api.url_for(ProductCollection))
        body.add_control("profile", PRODUCT_PROFILE)
        body.add_control_delete_product(handle)
        body.add_control_edit_product(handle)
        
        return Response(json.dumps(body), 200, mimetype=MASON)
    
    def put(self, handle):

        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, InventoryBuilder.product_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        if ((Product.query.filter_by(handle=request.json["handle"]).all())
            and (request.json["handle"] != handle)):
            return create_error_response(409,
                "Product handle already taken",
                "Trying to change the product handle to one already taken"
            )
        
        if not Product.query.filter_by(handle=handle).all():
            return create_error_response(404,
                "Not found",
                "Product does not exist"
            )
        
        try:
            prod = Product.query.filter_by(handle=handle).first()
            db.session.delete(prod)
            db.session.commit()

            prod = Product(
                handle=request.json["handle"],
                weight=float(request.json["weight"]),
                price=float(request.json["price"])
            )
            db.session.add(prod)
            db.session.commit()

            return Response(status=204)
        except Exception as e:
            return create_error_response(409, "Error", str(e))        

    def delete(self, handle):
        if not Product.query.filter_by(handle=handle).all():
            return create_error_response(404,
                "Not found",
                "Product does not exist"
            )
        
        prod = Product.query.filter_by(handle=handle).first()
        db.session.delete(prod)
        db.session.commit()

        return Response(status=204)


class ProductCollection(Resource):

    def get(self):
        body = InventoryBuilder(items=[])
        for product in Product.query.all():
            item = InventoryBuilder(
                handle=product.handle,
                weight=product.weight,
                price=product.price
            )
            item.add_control("self", api.url_for(ProductItem, handle=product.handle))
            item.add_control("profile", PRODUCT_PROFILE)
            body["items"].append(item)

        body.add_namespace("storage", LINK_RELATIONS_URL)
        body.add_control("self", api.url_for(ProductCollection))
        body.add_control("profile", PRODUCT_PROFILE)
        body.add_control_add_product()

        return Response(json.dumps(body), 200, mimetype=MASON)
        
    def post(self):
        
        if not request.json:
            return create_error_response(415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, InventoryBuilder.product_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        try:
            prod = Product(
                handle=request.json["handle"],
                weight=float(request.json["weight"]),
                price=float(request.json["price"])
            )
            db.session.add(prod)
            db.session.commit()
            
            headerDictionary = {}
            headerDictionary['Location'] = api.url_for(ProductItem, handle=request.json["handle"])
            
            return Response(status=201, headers=headerDictionary)
        except Exception as e:
            return create_error_response(409, "Error", str(e))
  
api.add_resource(ProductCollection, "/api/products/")
api.add_resource(ProductItem, "/api/products/<handle>/")

@app.route("/api/")
def api_entrypoint():
    body = MasonBuilder()
    body.add_namespace("storage", LINK_RELATIONS_URL + "#")
    body.add_control("storage:products-all", "/api/products/", method="GET")
    return Response(json.dumps(body), 200, mimetype=MASON)

@app.route(LINK_RELATIONS_URL)
def redirect_to_apiary_link_rels():
    return Response("", 200, mimetype=MASON)

@app.route(PRODUCT_PROFILE)
def redirect_to_apiary_product_profile():
    return Response("", 200, mimetype=MASON)

@app.route(STORAGE_PROFILE)
def redirect_to_apiary_storage_profile():
    return Response("", 200, mimetype=MASON)

@app.route(ERROR_PROFILE)
def redirect_to_apiary_error_profile():
    return Response("", 200, mimetype=MASON)