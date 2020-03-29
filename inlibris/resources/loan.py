from flask import request
from flask_restful import Resource
import json
from inlibris.models import Loan, Book, Patron

class LoanItem(Resource):
    def get(self, book_id):
        loan = Loan.query.filter_by(book_id=book_id).first()
        if loan is None:
            return 404

        book_barcode = Book.query.filter_by(id=book_id).first().barcode
        patron_barcode = Patron.query.filter_by(id=loan.patron_id).first().barcode

        loanInfo = {}
        loanInfo["book_barcode"] = book_barcode
        loanInfo["patron_barcode"] = patron_barcode
        loanInfo["loandate"] = str(loan.loandate)
        loanInfo["renewaldate"] = str(loan.renewaldate)
        loanInfo["duedate"] = str(loan.duedate)
        loanInfo["renewed"] = str(loan.renewed)
        loanInfo["status"] = loan.status

        return loanInfo, 200

class LoansByPatron(Resource):
    def get(self, patron_id):
        loans = Loan.query.filter_by(patron_id=patron_id).all()
        print(len(loans))
        loanList = []

        for loan in loans:
            loanInfo = {}
            book_barcode = Book.query.filter_by(id=loan.book_id).first().barcode
            patron_barcode = Patron.query.filter_by(id=patron_id).first().barcode
            loanInfo["book_barcode"] = book_barcode
            loanInfo["patron_barcode"] = patron_barcode
            loanInfo["loandate"] = str(loan.loandate)
            loanInfo["renewaldate"] = str(loan.renewaldate)
            loanInfo["duedate"] = str(loan.duedate)
            loanInfo["renewed"] = str(loan.renewed)
            loanInfo["status"] = loan.status
            loanList.append(loanInfo)

        return loanList, 200
