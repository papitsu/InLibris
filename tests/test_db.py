import os
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError

import app
from app import Patron, Item, Loan, Hold

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

@pytest.fixture
def db_handle():
    db_fd, db_fname = tempfile.mkstemp()
    app.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_fname
    app.app.config["TESTING"] = True
    
    with app.app.app_context():
        app.db.create_all()
        
    yield app.db
    
    app.db.session.remove()
    os.close(db_fd)
    os.unlink(db_fname)

def _get_patron(barcode="123456", email="test@test.com", firstname="Testi"):
    return Patron(
        barcode=barcode,
        firstname=firstname,
        email=email,
        regdate=datetime.now()
    )

def _get_item(barcode="234567", pubyear=2020):
    return Item(
        barcode=barcode,
        title="Testikirja",
        pubyear=pubyear,
        catdate=datetime.now()
    )

def _get_loan():
    return Loan(
        loandate=datetime.now(),
        duedate=datetime.now() + timedelta(days=28)
    )

def _get_hold():
    return Hold(
        holddate=datetime.now(),
        expirationdate=datetime.now() + timedelta(days=100)
    )

def test_create_instances(db_handle):
    """
    Tests that we can create one instance of each model and save them to the
    database using valid values for all columns. After creation, test that 
    everything can be found from database, and that all relationships have been
    saved correctly.
    """

    # Create everything
    patron = _get_patron()
    item = _get_item()
    loan = _get_loan()
    hold = _get_hold()
    loan.patron = patron
    loan.item = item
    hold.patron = patron
    hold.item = item
    db_handle.session.add(patron)
    db_handle.session.add(item)
    db_handle.session.add(hold)
    db_handle.session.add(loan)
    db_handle.session.commit()
    
    # Check that everything exists
    assert Patron.query.count() == 1
    assert Item.query.count() == 1
    assert Loan.query.count() == 1
    assert Hold.query.count() == 1
    db_patron = Patron.query.first()
    db_item = Item.query.first()
    db_loan = Loan.query.first()
    db_hold = Hold.query.first()
    
    # Check all relationships (both sides)
    assert db_loan.patron == patron
    assert db_loan.item == item
    assert db_hold.patron == patron
    assert db_hold.item == item
    assert db_hold in db_patron.holds
    assert db_loan in db_patron.loans
    assert db_hold in db_item.holds
    assert db_loan in db_item.loan

def test_delete_patron_and_item(db_handle):
    """
    Tests that we can create two instances of patron and item and save them to the
    database using valid values for all columns. After creation, test that 
    everything can be found from database. Then delete one intance of each model
    and check that there is only one instance of all models left.
    """

    # Create everything
    patron1 = _get_patron()
    patron2 = _get_patron(barcode="123789", email="test2@test.com")
    item1 = _get_item()
    item2 = _get_item(barcode="234789")
    
    db_handle.session.add(patron1)
    db_handle.session.add(item1)
    db_handle.session.add(patron2)
    db_handle.session.add(item2)

    db_handle.session.commit()
    
    # Check that everything exists
    assert Patron.query.count() == 2
    assert Item.query.count() == 2

    # Delete half
    db_handle.session.delete(patron2)
    db_handle.session.delete(item2)
    db_handle.session.commit()

    # Check amounts
    assert Patron.query.count() == 1
    assert Item.query.count() == 1

def test_loan_ondelete_patron(db_handle):
    """
    Tests that loan's patron foreign key is set to null when the patron
    is deleted.
    """
    
    # Create everything
    loan = _get_loan()
    patron = _get_patron()
    item = _get_item()
    loan.patron = patron
    loan.item = item
    db_handle.session.add(loan)
    db_handle.session.add(item)
    db_handle.session.add(patron)
    db_handle.session.commit()

    # Delete patron associated with the hold
    db_handle.session.delete(patron)
    db_handle.session.commit()

    # Check that foreign key is now null
    assert loan.patron is None

def test_loan_ondelete_item(db_handle):
    """
    Tests that loan is deleted when its item is deleted
    """
    
    # Create everything
    loan = _get_loan()
    patron = _get_patron()
    item = _get_item()
    loan.patron = patron
    loan.item = item
    db_handle.session.add(loan)
    db_handle.session.add(item)
    db_handle.session.add(patron)
    db_handle.session.commit()

    # Check that everything exists
    assert Patron.query.count() == 1
    assert Item.query.count() == 1
    assert Loan.query.count() == 1

    # Delete item
    db_handle.session.delete(item)
    db_handle.session.commit()

    # Check that item was deleted and as a consequence, the loan was deleted
    assert Patron.query.count() == 1
    assert Item.query.count() == 0
    assert Loan.query.count() == 0

def test_hold_ondelete_item(db_handle):
    """
    Tests that holds are deleted when their item is deleted
    """

    # Create everything
    hold1 = _get_hold()
    hold2 = _get_hold()
    patron1 = _get_patron()
    patron2 = _get_patron(barcode="123789", email="test2@test.com")
    item = _get_item()
    hold1.patron = patron1
    hold1.item = item
    hold2.patron = patron2
    hold2.item = item

    db_handle.session.add(hold1)
    db_handle.session.add(hold2)
    db_handle.session.add(item)
    db_handle.session.add(patron1)
    db_handle.session.add(patron2)
    db_handle.session.commit()

    # Check that everything exists
    assert Patron.query.count() == 2
    assert Item.query.count() == 1
    assert Hold.query.count() == 2

    # Delete item
    db_handle.session.delete(item)
    db_handle.session.commit()

    # Check that item was deleted and as a consequence, the holds were deleted
    assert Patron.query.count() == 2
    assert Item.query.count() == 0
    assert Hold.query.count() == 0

def test_hold_ondelete_patron(db_handle):
    """
    Tests that hold's patron foreign key is set to null when the patron
    is deleted.
    """
    
    # Create everything
    hold = _get_hold()
    patron = _get_patron()
    item = _get_item()
    hold.patron = patron
    hold.item = item
    db_handle.session.add(hold)
    db_handle.session.add(item)
    db_handle.session.add(patron)
    db_handle.session.commit()

    # Delete patron associated with the hold
    db_handle.session.delete(patron)
    db_handle.session.commit()

    # Check that foreign key is now null
    assert hold.patron is None

def test_uniqueness(db_handle):
    """
    Test that unique columns work as intended (patron barcode, patron email,
    item barcode, item_barcode for loans).
    """

    # Patron barcode must be unique
    patron1 = _get_patron(email="test1@test.com")
    patron2 = _get_patron(email="test2@test.com")
    db_handle.session.add(patron1)
    db_handle.session.add(patron2)    
    with pytest.raises(IntegrityError):
        db_handle.session.commit()

    db_handle.session.rollback()

    # Patron email must be unique
    patron1 = _get_patron(barcode="123456")
    patron2 = _get_patron(barcode="456789")
    db_handle.session.add(patron1)
    db_handle.session.add(patron2)    
    with pytest.raises(IntegrityError):
        db_handle.session.commit()

    db_handle.session.rollback()

    # Item barcode must be unique
    item1 = _get_item()
    item2 = _get_item()
    db_handle.session.add(item1)
    db_handle.session.add(item2)    
    with pytest.raises(IntegrityError):
        db_handle.session.commit()

    db_handle.session.rollback()

    # Loan must be one-to-one i.e. item_barcode must be unique
    item = _get_item()
    loan_1 = _get_loan()
    loan_2 = _get_loan()
    loan_1.item = item
    loan_2.item = item
    db_handle.session.add(item)
    db_handle.session.add(loan_1)
    db_handle.session.add(loan_2)    
    with pytest.raises(IntegrityError):
        db_handle.session.commit()

def test_query_filters(db_handle):
    """
    Test that we can query everything using multiple filters and find
    all, one, or some of the instances.
    """

    # Filter Patron queries by firstname, barcode and email
    patron1 = _get_patron(barcode="123456")
    patron2 = _get_patron(barcode="456789", email="test2@test.com")
    patron3 = _get_patron(barcode="789456", email="test3@test.com", firstname="Jussi")
    db_handle.session.add(patron1)
    db_handle.session.add(patron2)    
    db_handle.session.add(patron3)
    db_handle.session.commit()

    assert Patron.query.count() == 3
    assert Patron.query.filter_by(firstname="Testi").count() == 2
    assert Patron.query.filter_by(firstname="Jussi").count() == 1
    assert Patron.query.filter_by(barcode="456789").count() == 1
    assert Patron.query.filter(Patron.email!="test2@test.com").count() == 2

    # Filter Item queries
    item1 = _get_item()
    item2 = _get_item(barcode="234789")
    item3 = _get_item(barcode="256789", pubyear=2018)
    db_handle.session.add(item1)
    db_handle.session.add(item2)   
    db_handle.session.add(item3)   
    db_handle.session.commit()

    assert Item.query.count() == 3
    assert Item.query.filter_by(barcode="234789").count() == 1
    assert Item.query.filter_by(title="Testikirja").count() == 3
    assert Item.query.filter(Item.pubyear>2019).count() == 2

    # Filter Loan queries
    loan1 = _get_loan()
    loan2 = _get_loan()
    loan1.item = item1
    loan1.patron = patron1
    loan2.item = item2
    loan2.patron = patron1
    db_handle.session.add(loan1)
    db_handle.session.add(loan2)   
    db_handle.session.commit()

    assert Loan.query.count() == 2
    assert Loan.query.filter_by(patron_id=patron1.id).count() == 2
    assert Loan.query.filter_by(item_id=item1.id).count() == 1

    # Filter Hold queries
    hold1 = _get_hold()
    hold2 = _get_hold()
    hold1.item = item1
    hold1.patron = patron3
    hold2.item = item1
    hold2.patron = patron2
    db_handle.session.add(hold1)
    db_handle.session.add(hold2)   
    db_handle.session.commit()

    assert Hold.query.count() == 2
    assert Hold.query.filter_by(patron_id=patron1.id).count() == 0
    assert Hold.query.filter_by(patron_id=patron2.id).count() == 1
    assert Hold.query.filter_by(item_id=item1.id).count() == 2

def test_update_patron_barcode(db_handle):
    """
    Test that we can update the barcode of a patron. A patron is first created,
    the old barcode is saved and a new barcode is given. Then the old barcode 
    and the new barcode are compared.
    """
    
    # Create everything
    patron = _get_patron()
    db_handle.session.add(patron)
    db_handle.session.commit()
    
    # Check that everything exists
    assert Patron.query.count() == 1
    db_patron = Patron.query.first()

    old_barcode = db_patron.barcode
    db_patron.barcode = '111111'
    db_handle.session.commit()

    db_patron = Patron.query.first()
    assert db_patron.barcode != old_barcode

def test_update_item_barcode(db_handle):
    """
    Test that we can update the barcode of an item. An item is first created,
    the old barcode is saved and a new barcode is given. Then the old barcode 
    and the new barcode are compared.
    """
    
    # Create everything
    item = _get_item()
    db_handle.session.add(item)
    db_handle.session.commit()
    
    # Check that everything exists
    assert Item.query.count() == 1
    db_item = Item.query.first()

    old_barcode = db_item.barcode
    db_item.barcode = '211111'
    db_handle.session.commit()

    db_item = Item.query.first()
    assert db_item.barcode != old_barcode

def test_update_loan_item(db_handle):
    """
    Test that we can update the item of a loan.
    """
    
    # Create everything
    item1 = _get_item()
    loan = _get_loan()
    patron = _get_patron()
    loan.item = item1
    loan.patron = patron
    
    db_handle.session.add(item1)
    db_handle.session.add(patron)
    db_handle.session.add(loan)
    db_handle.session.commit()
    
    # Check that everything exists
    assert Item.query.count() == 1
    assert Patron.query.count() == 1
    assert Item.query.count() == 1
    db_loan = Loan.query.first()
    old_item_id = db_loan.item_id

    # Change item associated with the loan and commit
    item2 = _get_item(barcode="274185")
    loan.item = item2
    db_handle.session.add(item2)
    db_handle.session.commit()

    # Check that item has changed
    db_loan = Loan.query.first()
    assert db_loan.item_id != old_item_id

def test_update_hold_patron(db_handle):
    """
    Test that we can update the patron of a hold.
    """
    
    # Create everything
    item = _get_item()
    hold = _get_hold()
    patron1 = _get_patron()
    hold.item = item
    hold.patron = patron1
    
    db_handle.session.add(item)
    db_handle.session.add(patron1)
    db_handle.session.add(hold)
    db_handle.session.commit()
    
    # Check that everything exists
    assert Item.query.count() == 1
    assert Patron.query.count() == 1
    assert Hold.query.count() == 1
    db_hold = Hold.query.first()
    old_patron_id = db_hold.patron_id

    # Change patron associated with the hold and commit
    patron2 = _get_patron(barcode="123852", email="posti@posio.fi")
    hold.patron = patron2
    db_handle.session.add(patron2)
    db_handle.session.commit()
    
    # Check that patron has changed
    db_hold = Hold.query.first()
    assert db_hold.patron_id != old_patron_id

def test_delete_hold(db_handle):
    """
    Test that we can delete a hold correctly.
    """
    
    # Create everything
    item = _get_item()
    hold = _get_hold()
    patron = _get_patron()
    hold.item = item
    hold.patron = patron
    
    db_handle.session.add(item)
    db_handle.session.add(patron)
    db_handle.session.add(hold)
    db_handle.session.commit()
    
    # Check that everything exists
    assert Item.query.count() == 1
    assert Patron.query.count() == 1
    assert Hold.query.count() == 1

    # Delete hold
    db_handle.session.delete(hold)
    db_handle.session.commit()

    # Check that the right thing has changed
    assert Item.query.count() == 1
    assert Patron.query.count() == 1
    assert Hold.query.count() == 0

def test_delete_loan(db_handle):
    """
    Test that we can delete a loan correctly.
    """
    
    # Create everything
    item = _get_item()
    loan = _get_loan()
    patron = _get_patron()
    loan.item = item
    loan.patron = patron
    
    db_handle.session.add(item)
    db_handle.session.add(patron)
    db_handle.session.add(loan)
    db_handle.session.commit()
    
    # Check that everything exists
    assert Item.query.count() == 1
    assert Patron.query.count() == 1
    assert Loan.query.count() == 1

    # Delete hold
    db_handle.session.delete(loan)
    db_handle.session.commit()

    # Check that the right thing has changed
    assert Item.query.count() == 1
    assert Patron.query.count() == 1
    assert Loan.query.count() == 0
