from app import db, Patron, Item, Hold, Loan
from datetime import datetime, timedelta

db.create_all()

patron1 = Patron(
    barcode="100001",
    firstname="Hilma",
    lastname="Kirjastontäti",
    email="hilma@kirjasto.fi",
    group="Staff",
    status="Active",
    regdate=datetime(2020,1,1,13,37,00)
)

patron2 = Patron(
    barcode="100002",
    firstname="Testi",
    lastname="Käyttäjä",
    email="kayttaja@test.com",
    regdate=datetime(1999,12,31,23,59,59)
)

item1 = Item(
    barcode="200001",
    title="Garpin maailma",
    author="Irving, John",
    pubyear=2011,
    format="book",
    description="ISBN 978-951-31-1264-6",
    catdate=datetime(2020,2,13,15,13,45)
)

item2 = Item(
    barcode="200002",
    title="Minä olen monta",
    author="Irving, John",
    pubyear=2013,
    format="book",
    description="ISBN 978-951-31-7092-9",
    catdate=datetime(2020,2,13,15,15,15)
)

item3 = Item(
    barcode="200003",
    title="Oman elämänsä sankari",
    author="Irving, John",
    pubyear=2009,
    format="book",
    description="ISBN 978-951-31-6307-8",
    catdate=datetime(2020,2,13,15,17,5)
)

loan1 = Loan(
    item=item1,
    patron=patron2,
    loandate=datetime.now(),
    duedate=datetime.now() + timedelta(days=28)
)

loan2 = Loan(
    item=item3,
    patron=patron2,
    loandate=datetime.now(),
    duedate=datetime.now() + timedelta(days=28)
)

hold1 = Hold(
    item=item1,
    patron=patron1,
    holddate=datetime.now(),
    expirationdate=datetime.now() + timedelta(days=45)
)

hold2 = Hold(
    item=item3,
    patron=patron1,
    holddate=datetime.now() + timedelta(hours=1),
    expirationdate=datetime.now() + timedelta(hours=1, days=45)
)

db.session.add(patron1)
db.session.add(patron2)
db.session.add(item1)
db.session.add(item2)
db.session.add(item3)
db.session.add(loan1)
db.session.add(loan2)
db.session.add(hold1)
db.session.add(hold2)
db.session.commit()