import os
import pytest
import json
import tempfile
from datetime import datetime, timedelta
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError

from inlibris import create_app, db
from inlibris.models import Patron, Book, Loan
from tests import utils

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# based on http://flask.pocoo.org/docs/1.0/testing/
# we don't need a client for database testing, just the db handle
@pytest.fixture
def client():
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True
    }
    
    app = create_app(config)

    with app.app_context():
        db.create_all()
        utils._populate_db(db)

    yield app.test_client()

    db.session.remove()
    os.close(db_fd)
    os.unlink(db_fname)

class TestEntryPoint(object):
    """
    This class tests the API entry point.
    """

    RESOURCE_URL = "/api/"

    def test_get(self, client):
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        utils._check_namespace(client, body)
        utils._check_control_get_method("inlibris:books-all", client, body)
        utils._check_control_get_method("inlibris:patrons-all", client, body)

class TestPatronCollection(object):
    """
    This class implements tests for each HTTP method in patron collection
    resource. 
    """

    RESOURCE_URL = "/api/patrons/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work. Also checks that all of the items from
        the DB population are present, and their controls.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        utils._check_namespace(client, body)
        utils._check_control_get_method("self", client, body)
        utils._check_control_get_method("profile", client, body)
        utils._check_control_get_method("inlibris:books-all", client, body)
        utils._check_control_post_patron_method("inlibris:add-patron", client, body)
        assert len(body["items"]) == 2
        for item in body["items"]:
            utils._check_control_get_method("self", client, item)
            utils._check_control_get_method("profile", client, item)
            assert "id" in item
            assert "barcode" in item
            assert "firstname" in item
            assert "lastname" in item
            assert "email" in item
            assert "group" in item
            assert "status" in item

    def test_post(self, client):
        """
        Tests the POST method. Checks all of the possible error codes, and 
        also checks that a valid request receives a 201 response with a 
        location header that leads into the newly created resource.
        """
        
        valid = utils._get_patron_json()
        
        # test with wrong content type
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415

        # test with valid and see that it exists afterward
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.headers["Location"].endswith(self.RESOURCE_URL + "3" + "/")
        resp = client.get(resp.headers["Location"])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["barcode"] == 123456
        assert body["firstname"] == "Testi"
        assert body["email"] == "test@test.com"

        # send same data again for 409
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

        # send data with same email for 409
        valid = utils._get_patron_json(barcode=123457)
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        # remove model field for 400
        valid.pop("email")
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

class TestPatronItem(object):
    """
    This class implements tests for each HTTP method in patron item
    resource. 
    """

    RESOURCE_URL = "/api/patrons/1/"
    INVALID_URL = "/api/patrons/15/"
    
    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["barcode"] == 100001
        assert body["firstname"] == "Hilma"
        assert body["lastname"] == "Kirjastontäti"
        assert body["email"] == "hilma@kirjasto.fi"
        assert body["group"] == "Staff"
        assert body["status"] == "Active"
        utils._check_namespace(client, body)
        utils._check_control_get_method("profile", client, body)
        utils._check_control_get_method("collection", client, body)
        utils._check_control_put_patron_method("edit", client, body)
        utils._check_control_delete_method("inlibris:delete", client, body)

        # test invalid URL
        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404


    def test_put(self, client):
        """
        Tests the PUT method. Checks all of the possible error codes, and also
        checks that a valid request receives a 204 response.
        """
        
        valid = utils._get_patron_json()
        
        # test with wrong content type
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        # test invalid URL
        resp = client.put(self.INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        # test with another patron's barcode
        valid["barcode"] = 100002
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        # test with valid
        valid["barcode"] = 100001
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204
        
        # remove field for 400
        valid.pop("email")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

    def test_delete(self, client):
        """
        Tests the DELETE method. Checks that a valid request reveives 204
        response and that trying to GET the patron afterwards results in 404.
        Also checks that trying to delete a patron that doesn't exist results
        in 404.
        """
        
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 404
        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404

class TestBookCollection(object):
    """
    This class implements tests for each HTTP method in book collection
    resource. 
    """
    
    RESOURCE_URL = "/api/books/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work. Also checks that all of the items from
        the DB popluation are present, and their controls.
        """
        
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        utils._check_namespace(client, body)
        utils._check_control_get_method("self", client, body)
        utils._check_control_get_method("profile", client, body)
        utils._check_control_get_method("inlibris:patrons-all", client, body)
        utils._check_control_post_book_method("inlibris:add-book", client, body)
        assert len(body["items"]) == 3
        for item in body["items"]:
            utils._check_control_get_method("self", client, item)
            utils._check_control_get_method("profile", client, item)
            assert "id" in item
            assert "barcode" in item
            assert "title" in item
            assert "author" in item
            assert "pubyear" in item
            assert "format" in item
            assert "description" in item
            assert "loantime" in item
            assert "renewlimit" in item


    def test_post(self, client):
        """
        Tests the POST method. Checks all of the possible error codes, and 
        also checks that a valid request receives a 201 response with a 
        location header that leads into the newly created resource.
        """
        
        valid = utils._get_book_json()
        
        # test with wrong content type
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        # test with valid and see that it exists afterward
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.headers["Location"].endswith(self.RESOURCE_URL + "4" + "/")
        resp = client.get(resp.headers["Location"])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["barcode"] == 234567
        assert body["title"] == "Testikirja"
        assert body["pubyear"] == 2020
        
        # send same data again for 409
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        # remove pubyear field for 400
        valid.pop("pubyear")
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400


class TestBookItem(object):
    """
    This class implements tests for each HTTP method in book item
    resource. 
    """

    RESOURCE_URL = "/api/books/1/"
    INVALID_URL = "/api/books/14/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["barcode"] == 200001
        assert body["title"] == "Garpin maailma"
        assert body["pubyear"] == 2011
        utils._check_namespace(client, body)
        utils._check_control_get_method("self", client, body)
        utils._check_control_get_method("profile", client, body)
        utils._check_control_get_method("collection", client, body)
        utils._check_control_get_method("inlibris:holds-on", client, body)
        utils._check_control_get_method("inlibris:loan-of", client, body)
        utils._check_control_put_book_method("edit", client, body)
        utils._check_control_delete_method("inlibris:delete", client, body)
        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404
    
    def test_put(self, client):
        """
        Tests the PUT method. Checks all of the possible error codes, and also
        checks that a valid request receives a 204 response.
        """
        
        valid = utils._get_book_json()
        
        # test with wrong content type
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        # test invalid URL
        resp = client.put(self.INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        # test with another book's barcode
        valid["barcode"] = 200002
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        # test with valid
        valid["barcode"] = 200001
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204
        
        # remove field for 400
        valid.pop("pubyear")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400
    

    def test_delete(self, client):
        """
        Tests the DELETE method. Checks that a valid request reveives 204
        response and that trying to GET the book afterwards results in 404.
        Also checks that trying to delete a book that doesn't exist results
        in 404.
        """
        
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204
        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 404
        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404

class TestLoanItem(object):
    """
    This class implements tests for each HTTP method in loan item
    resource. 
    """

    RESOURCE_URL = "/api/books/1/loan/"
    NOT_LOANED_URL = "/api/books/3/loan/"
    NO_BOOK_URL = "/api/books/14/loan/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["id"] == 1
        assert body["book_barcode"] == 200001
        assert body["patron_barcode"] == 100002
        assert body["loandate"] == "2020-04-02"
        assert body["renewaldate"] == None
        assert body["duedate"] == "2020-04-30"
        assert body["renewed"] == 0
        assert body["status"] == "Charged"
        utils._check_namespace(client, body)
        utils._check_control_get_method("self", client, body)
        utils._check_control_get_method("profile", client, body)
        utils._check_control_get_method("author", client, body)
        utils._check_control_get_method("inlibris:loans-by", client, body)
        utils._check_control_get_method("inlibris:target-book", client, body)
        utils._check_control_get_method("inlibris:books-all", client, body)
        utils._check_control_get_method("inlibris:patrons-all", client, body)
        utils._check_control_put_loan_method("edit", client, body)
        utils._check_control_delete_method("inlibris:delete", client, body)
        resp = client.get(self.NO_BOOK_URL)
        assert resp.status_code == 404
        resp = client.get(self.NOT_LOANED_URL)
        assert resp.status_code == 204

    def test_put(self, client):
        """
        Tests the PUT method. Checks all of the possible error codes, and also
        checks that a valid request receives a 204 response.
        """
        
        valid = utils._get_edit_loan_json()
        
        # test with wrong content type
        resp = client.put(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        # test invalid URL
        resp = client.put(self.NO_BOOK_URL, json=valid)
        assert resp.status_code == 404

         # test invalid patron barcode
        valid["patron_barcode"] = 100014
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 404
        
        # test with valid
        valid["patron_barcode"] = 100001
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 200
        
        # reset previous
        valid["patron_barcode"] = 100002
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 200

        # test book which not loaned
        resp = client.put(self.NOT_LOANED_URL, json=valid)
        assert resp.status_code == 204

        # remove field for 400
        valid.pop("patron_barcode")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

        # try without renewaldate
        valid = utils._get_edit_loan_json()
        valid.pop("renewaldate")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 200

        # try without renewed
        valid.pop("renewed")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 200

        # try without status
        valid.pop("status")
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 200

    def test_delete(self, client):
        """
        Tests the DELETE method. Checks that a valid request reveives 204
        response and that trying to GET the loan afterwards results in 404.
        Also checks that trying to delete a loan that doesn't exist results
        in 404.
        """
        
        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204
        resp = client.delete(self.NOT_LOANED_URL)
        assert resp.status_code == 204
        resp = client.delete(self.NO_BOOK_URL)
        assert resp.status_code == 404

class TestLoansByPatron(object):
    """
    This class implements tests for each HTTP method in loans by patron collection
    resource. 
    """

    RESOURCE_URL = "/api/patrons/2/loans/"
    NO_PATRON_URL = "/api/patrons/13/loans/"

    def test_get(self, client):
        """
        Tests the GET method. Checks that the response status code is 200, and
        then checks that all of the expected attributes and controls are
        present, and the controls work. Also checks that all of the items from
        the DB popluation are present, and their controls.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        utils._check_namespace(client, body)
        utils._check_control_get_method("self", client, body)
        utils._check_control_get_method("profile", client, body)
        utils._check_control_get_method("author", client, body)
        utils._check_control_get_method("inlibris:books-all", client, body)
        utils._check_control_get_method("inlibris:patrons-all", client, body)
        utils._check_control_post_loan_method("inlibris:add-loan", client, body)
        assert len(body["items"]) == 2
        for item in body["items"]:
            utils._check_control_get_method("self", client, item)
            utils._check_control_get_method("profile", client, item)
            assert "id" in item
            assert "book_barcode" in item
            assert "patron_barcode" in item
            assert "loandate" in item
            assert "renewaldate" in item
            assert "duedate" in item
            assert "renewed" in item
            assert "status" in item

    
    def test_post(self, client):
        """
        Tests the POST method. Checks all of the possible error codes, and 
        also checks that a valid request receives a 201 response with a 
        location header that leads into the newly created resource.
        """
        
        valid = utils._get_add_loan_json()
        
        # test with wrong content type
        resp = client.post(self.RESOURCE_URL, data=json.dumps(valid))
        assert resp.status_code == 415
        
        # test with valid and see that it exists afterward
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.headers["Location"].endswith("/api/books/3/loan/")
        resp = client.get(resp.headers["Location"])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["book_barcode"] == 200002
        assert body["patron_barcode"] == 100002
        assert body["loandate"] == str(datetime.now().date())
        assert body["renewed"] == 0
        assert body["status"] == "Charged"

        # send same data again for 409
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

        # delete previous
        resp = client.delete("/api/books/3/loan/")
        assert resp.status_code == 204

        # send with custom duedate
        valid["duedate"] = "2020-08-08"
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.headers["Location"].endswith("/api/books/3/loan/")
        resp = client.get(resp.headers["Location"])
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["book_barcode"] == 200002
        assert body["patron_barcode"] == 100002
        assert body["loandate"] == str(datetime.now().date())
        assert body["renewed"] == 0
        assert body["status"] == "Charged"

        # send to nonexistent patron for 404
        resp = client.post(self.NO_PATRON_URL, json=valid)
        assert resp.status_code == 404

        # send invalid book barcode for 404
        valid["book_barcode"] = 200014
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 404
        
        # post wrong JSON for 400
        valid = utils._get_patron_json()
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400
    