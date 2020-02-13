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

def _get_patron(barcode="123456", email="test@test.com"):
    return Patron(
        barcode=barcode,
        firstname="Testinimi",
        email=email,
        regdate=datetime.now()
    )

def _get_item(barcode="234567"):
    return Item(
        barcode=barcode,
        title="Testikirja",
        pubyear=2020,
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

def test_item_loan_one_to_one(db_handle):
    """
    Tests that the relationship between item and loan is one-to-one.
    i.e. that we cannot assign the same item for two loans.
    """
    
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