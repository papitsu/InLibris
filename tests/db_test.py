import os
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError

from inlibris import create_app, db
from inlibris.models import Patron, Book, Hold, Loan

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

@pytest.fixture(scope="session")
def app():
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True
    }
    
    app = create_app(config)

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    os.close(db_fd)
    os.unlink(db_fname)

def _get_patron(barcode=123456, email="test@test.com", firstname="Testi"):
    return Patron(
        barcode=barcode,
        firstname=firstname,
        email=email,
        regdate=datetime.now().date()
    )

def _get_book(barcode=234567, pubyear=2020):
    return Book(
        barcode=barcode,
        title="Testikirja",
        pubyear=pubyear
    )

def _get_loan():
    return Loan(
        loandate=datetime.now().date(),
        duedate=(datetime.now() + timedelta(days=28)).date()
    )

def _get_hold():
    return Hold(
        holddate=datetime.now().date(),
        expirationdate=(datetime.now() + timedelta(days=100)).date()
    )

def test_create_instances(app):
    """
    Tests that we can create one instance of each model and save them to the
    database using valid values for all columns. After creation, test that 
    everything can be found from database, and that all relationships have been
    saved correctly.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create everything
        patron = _get_patron()
        book = _get_book()
        loan = _get_loan()
        hold = _get_hold()
        loan.patron = patron
        loan.book = book
        hold.patron = patron
        hold.book = book
        db.session.add(patron)
        db.session.add(book)
        db.session.add(hold)
        db.session.add(loan)
        db.session.commit()
        
        # Check that everything exists
        assert Patron.query.count() == 1
        assert Book.query.count() == 1
        assert Loan.query.count() == 1
        assert Hold.query.count() == 1
        db_patron = Patron.query.first()
        db_item = Book.query.first()
        db_loan = Loan.query.first()
        db_hold = Hold.query.first()
        
        # Check all relationships (both sides)
        assert db_loan.patron == patron
        assert db_loan.book == book
        assert db_hold.patron == patron
        assert db_hold.book == book
        assert db_hold in db_patron.holds
        assert db_loan in db_patron.loans
        assert db_hold in db_item.holds
        assert db_loan in db_item.loan

def test_delete_patron_and_item(app):
    """
    Tests that we can create two instances of patron and book and save them to the
    database using valid values for all columns. After creation, test that 
    everything can be found from database. Then delete one intance of each model
    and check that there is only one instance of all models left.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create everything
        patron1 = _get_patron()
        patron2 = _get_patron(barcode=123789, email="test2@test.com")
        book1 = _get_book()
        book2 = _get_book(barcode=234789)
        
        db.session.add(patron1)
        db.session.add(book1)
        db.session.add(patron2)
        db.session.add(book2)

        db.session.commit()
        
        # Check that everything exists
        assert Patron.query.count() == 2
        assert Book.query.count() == 2

        # Delete half
        db.session.delete(patron2)
        db.session.delete(book2)
        db.session.commit()

        # Check amounts
        assert Patron.query.count() == 1
        assert Book.query.count() == 1

def test_loan_ondelete_patron(app):
    """
    Tests that loan's patron foreign key is set to null when the patron
    is deleted.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create everything
        loan = _get_loan()
        patron = _get_patron()
        book = _get_book()
        loan.patron = patron
        loan.book = book
        db.session.add(loan)
        db.session.add(book)
        db.session.add(patron)
        db.session.commit()

        # Delete patron associated with the hold
        db.session.delete(patron)
        db.session.commit()

        # Check that foreign key is now null
        assert loan.patron is None

def test_loan_ondelete_item(app):
    """
    Tests that loan is deleted when its book is deleted
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Create everything
        loan = _get_loan()
        patron = _get_patron()
        book = _get_book()
        loan.patron = patron
        loan.book = book
        db.session.add(loan)
        db.session.add(book)
        db.session.add(patron)
        db.session.commit()

        # Check that everything exists
        assert Patron.query.count() == 1
        assert Book.query.count() == 1
        assert Loan.query.count() == 1

        # Delete book
        db.session.delete(book)
        db.session.commit()

        # Check that book was deleted and as a consequence, the loan was deleted
        assert Patron.query.count() == 1
        assert Book.query.count() == 0
        assert Loan.query.count() == 0

def test_hold_ondelete_item(app):
    """
    Tests that holds are deleted when their book is deleted
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create everything
        hold1 = _get_hold()
        hold2 = _get_hold()
        patron1 = _get_patron()
        patron2 = _get_patron(barcode=123789, email="test2@test.com")
        book = _get_book()
        hold1.patron = patron1
        hold1.book = book
        hold2.patron = patron2
        hold2.book = book

        db.session.add(hold1)
        db.session.add(hold2)
        db.session.add(book)
        db.session.add(patron1)
        db.session.add(patron2)
        db.session.commit()

        # Check that everything exists
        assert Patron.query.count() == 2
        assert Book.query.count() == 1
        assert Hold.query.count() == 2

        # Delete book
        db.session.delete(book)
        db.session.commit()

        # Check that book was deleted and as a consequence, the holds were deleted
        assert Patron.query.count() == 2
        assert Book.query.count() == 0
        assert Hold.query.count() == 0

def test_hold_ondelete_patron(app):
    """
    Tests that hold's patron foreign key is set to null when the patron
    is deleted.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Create everything
        hold = _get_hold()
        patron = _get_patron()
        book = _get_book()
        hold.patron = patron
        hold.book = book
        db.session.add(hold)
        db.session.add(book)
        db.session.add(patron)
        db.session.commit()

        # Delete patron associated with the hold
        db.session.delete(patron)
        db.session.commit()

        # Check that foreign key is now null
        assert hold.patron is None

def test_uniqueness(app):
    """
    Test that unique columns work as intended (patron barcode, patron email,
    book barcode, item_barcode for loans).
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Patron barcode must be unique
        patron1 = _get_patron(email="test1@test.com")
        patron2 = _get_patron(email="test2@test.com")
        db.session.add(patron1)
        db.session.add(patron2)    
        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()

        # Patron email must be unique
        patron1 = _get_patron(barcode="123456")
        patron2 = _get_patron(barcode="456789")
        db.session.add(patron1)
        db.session.add(patron2)    
        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()

        # Book barcode must be unique
        book1 = _get_book()
        book2 = _get_book()
        db.session.add(book1)
        db.session.add(book2)    
        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()

        # Loan must be one-to-one i.e. item_barcode must be unique
        book = _get_book()
        loan_1 = _get_loan()
        loan_2 = _get_loan()
        loan_1.book = book
        loan_2.book = book
        db.session.add(book)
        db.session.add(loan_1)
        db.session.add(loan_2)    
        with pytest.raises(IntegrityError):
            db.session.commit()

def test_query_filters(app):
    """
    Test that we can query everything using multiple filters and find
    all, one, or some of the instances.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Filter Patron queries by firstname, barcode and email
        patron1 = _get_patron(barcode="123456")
        patron2 = _get_patron(barcode="456789", email="test2@test.com")
        patron3 = _get_patron(barcode="789456", email="test3@test.com", firstname="Jussi")
        db.session.add(patron1)
        db.session.add(patron2)    
        db.session.add(patron3)
        db.session.commit()

        assert Patron.query.count() == 3
        assert Patron.query.filter_by(firstname="Testi").count() == 2
        assert Patron.query.filter_by(firstname="Jussi").count() == 1
        assert Patron.query.filter_by(barcode="456789").count() == 1
        assert Patron.query.filter(Patron.email!="test2@test.com").count() == 2

        # Filter Book queries
        book1 = _get_book()
        book2 = _get_book(barcode="234789")
        book3 = _get_book(barcode="256789", pubyear=2018)
        db.session.add(book1)
        db.session.add(book2)   
        db.session.add(book3)   
        db.session.commit()

        assert Book.query.count() == 3
        assert Book.query.filter_by(barcode="234789").count() == 1
        assert Book.query.filter_by(title="Testikirja").count() == 3
        assert Book.query.filter(Book.pubyear>2019).count() == 2

        # Filter Loan queries
        loan1 = _get_loan()
        loan2 = _get_loan()
        loan1.book = book1
        loan1.patron = patron1
        loan2.book = book2
        loan2.patron = patron1
        db.session.add(loan1)
        db.session.add(loan2)   
        db.session.commit()

        assert Loan.query.count() == 2
        assert Loan.query.filter_by(patron_id=patron1.id).count() == 2
        assert Loan.query.filter_by(book_id=book1.id).count() == 1

        # Filter Hold queries
        hold1 = _get_hold()
        hold2 = _get_hold()
        hold1.book = book1
        hold1.patron = patron3
        hold2.book = book1
        hold2.patron = patron2
        db.session.add(hold1)
        db.session.add(hold2)   
        db.session.commit()

        assert Hold.query.count() == 2
        assert Hold.query.filter_by(patron_id=patron1.id).count() == 0
        assert Hold.query.filter_by(patron_id=patron2.id).count() == 1
        assert Hold.query.filter_by(book_id=book1.id).count() == 2

def test_update_patron_barcode(app):
    """
    Test that we can update the barcode of a patron. A patron is first created,
    the old barcode is saved and a new barcode is given. Then the old barcode 
    and the new barcode are compared.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Create everything
        patron = _get_patron()
        db.session.add(patron)
        db.session.commit()
        
        # Check that everything exists
        assert Patron.query.count() == 1
        db_patron = Patron.query.first()

        old_barcode = db_patron.barcode
        db_patron.barcode = '111111'
        db.session.commit()

        db_patron = Patron.query.first()
        assert db_patron.barcode != old_barcode

def test_update_item_barcode(app):
    """
    Test that we can update the barcode of an book. An book is first created,
    the old barcode is saved and a new barcode is given. Then the old barcode 
    and the new barcode are compared.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Create everything
        book = _get_book()
        db.session.add(book)
        db.session.commit()
        
        # Check that everything exists
        assert Book.query.count() == 1
        db_item = Book.query.first()

        old_barcode = db_item.barcode
        db_item.barcode = '211111'
        db.session.commit()

        db_item = Book.query.first()
        assert db_item.barcode != old_barcode

def test_update_loan_item(app):
    """
    Test that we can update the book of a loan.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Create everything
        book1 = _get_book()
        loan = _get_loan()
        patron = _get_patron()
        loan.book = book1
        loan.patron = patron
        
        db.session.add(book1)
        db.session.add(patron)
        db.session.add(loan)
        db.session.commit()
        
        # Check that everything exists
        assert Book.query.count() == 1
        assert Patron.query.count() == 1
        assert Book.query.count() == 1
        db_loan = Loan.query.first()
        old_book_id = db_loan.book_id

        # Change book associated with the loan and commit
        book2 = _get_book(barcode="274185")
        loan.book = book2
        db.session.add(book2)
        db.session.commit()

        # Check that book has changed
        db_loan = Loan.query.first()
        assert db_loan.book_id != old_book_id

def test_update_hold_patron(app):
    """
    Test that we can update the patron of a hold.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Create everything
        book = _get_book()
        hold = _get_hold()
        patron1 = _get_patron()
        hold.book = book
        hold.patron = patron1
        
        db.session.add(book)
        db.session.add(patron1)
        db.session.add(hold)
        db.session.commit()
        
        # Check that everything exists
        assert Book.query.count() == 1
        assert Patron.query.count() == 1
        assert Hold.query.count() == 1
        db_hold = Hold.query.first()
        old_patron_id = db_hold.patron_id

        # Change patron associated with the hold and commit
        patron2 = _get_patron(barcode="123852", email="posti@posio.fi")
        hold.patron = patron2
        db.session.add(patron2)
        db.session.commit()
        
        # Check that patron has changed
        db_hold = Hold.query.first()
        assert db_hold.patron_id != old_patron_id

def test_delete_hold(app):
    """
    Test that we can delete a hold correctly.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create everything
        book = _get_book()
        hold = _get_hold()
        patron = _get_patron()
        hold.book = book
        hold.patron = patron
        
        db.session.add(book)
        db.session.add(patron)
        db.session.add(hold)
        db.session.commit()
        
        # Check that everything exists
        assert Book.query.count() == 1
        assert Patron.query.count() == 1
        assert Hold.query.count() == 1

        # Delete hold
        db.session.delete(hold)
        db.session.commit()

        # Check that the right thing has changed
        assert Book.query.count() == 1
        assert Patron.query.count() == 1
        assert Hold.query.count() == 0

def test_delete_loan(app):
    """
    Test that we can delete a loan correctly.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
    
        # Create everything
        book = _get_book()
        loan = _get_loan()
        patron = _get_patron()
        loan.book = book
        loan.patron = patron
        
        db.session.add(book)
        db.session.add(patron)
        db.session.add(loan)
        db.session.commit()
        
        # Check that everything exists
        assert Book.query.count() == 1
        assert Patron.query.count() == 1
        assert Loan.query.count() == 1

        # Delete hold
        db.session.delete(loan)
        db.session.commit()

        # Check that the right thing has changed
        assert Book.query.count() == 1
        assert Patron.query.count() == 1
        assert Loan.query.count() == 0
