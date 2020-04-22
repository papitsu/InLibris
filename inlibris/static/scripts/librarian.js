//"use strict";

const DEBUG = true;
const MASONJSON = "application/vnd.mason+json";
const PLAINJSON = "application/json";

var current_book_object = null;
var current_patron_object = null;
var all_patrons = null;

function renderError(jqxhr) {
    let msg = jqxhr.responseJSON["@error"]["@message"];
    $("div.notification").html("<p class='error'>" + msg + "</p>");
}

function renderMsg(msg) {
    $("div.notification").html("<p class='msg'>" + msg + "</p>");
}

function getResource(href, renderer) {
    $.ajax({
        url: href,
        success: renderer,
        error: renderError
    });
}

function sendData(href, method, item, postProcessor) {
    $.ajax({
        url: href,
        type: method,
        data: JSON.stringify(item),
        contentType: PLAINJSON,
        processData: false,
        success: postProcessor,
        error: renderError
    });
}

function followLink(event, a, renderer) {
    event.preventDefault();
    getResource($(a).attr("href"), renderer);
}

function emptySecondTable() {
    $("div.secondtabletitle").empty();
    $(".secondresulttable thead").empty();
    $(".secondresulttable tbody").empty();
}

function renderEntrypoint(body) {
    $("div.navigation").html(
        "<a href='" +
        body["@controls"]["inlibris:patrons-all"].href +
        "' onClick='followLink(event, this, renderPatrons)'>Patrons</a>"
        + " | " +
        "<a href='" +
        body["@controls"]["inlibris:books-all"].href +
        "' onClick='followLink(event, this, renderBooks)'>Books</a>"
    );
    $(".firstresulttable thead").empty();
    $(".firstresulttable tbody").empty();
    $("div.form").empty();
    emptySecondTable();
}

function patronRow(item) {
    let link = "<a href='" +
            item["@controls"].self.href +
            "' onClick='followLink(event, this, renderPatron)'>show</a>";

    return "<tr><td>" + item.barcode +
            "</td><td>" + item.firstname +
            "</td><td>" + item.lastname +
            "</td><td>" + link + "</td></tr>";
}

function renderPatrons(body) {
    current_book_object = null;
    current_patron_object = null;

    var items = body.items;
    items.sort(function(a, b) {
        return (a.barcode - b.barcode);
    });

    $("div.navigation").html(
        "<a href='" +
        body["@controls"].self.href +
        "' onClick='followLink(event, this, renderPatrons)'>Patrons</a>"
        + " | " +
        "<a href='" +
        body["@controls"]["inlibris:books-all"].href +
        "' onClick='followLink(event, this, renderBooks)'>Books</a>"
    );
    $(".firsttabletitle").html("<h3>Patrons</h3>");
    $(".firstresulttable thead").html(
        "<tr><th>Barcode</th><th>First name</th><th>Last name</th><th>Actions</th></tr>"
    );   
    let tbody = $(".firstresulttable tbody");
    tbody.empty();
    items.forEach(function (item) {
        tbody.append(patronRow(item));
    });
    $("div.form").empty();
    emptySecondTable();
}

function refreshPatron(item) {
    let href = item["@controls"].author.href;
    if (href) {
        getResource(href, renderPatron);
    }
}

function renewLoan(item) {
    $.ajax({
        url: item["@controls"]["inlibris:target-book"].href,
        success: function(data) {
            if (item.renewed < data.renewlimit) {
                item.renewed = item.renewed + 1;
                let m = new Date();
                item.renewaldate = m.getUTCFullYear() + "-" + (m.getUTCMonth() + 1) + "-" + m.getUTCDate();
                m.setDate(m.getDate() + data.loantime);
                item.duedate = m.getUTCFullYear() + "-" + (m.getUTCMonth() + 1) + "-" + m.getUTCDate();
                item.status = "Renewed";
                sendData(item["@controls"].edit.href, item["@controls"].edit.method, item, refreshPatron(item));
            }
        },
        error: renderError
    });
}

function returnLoan(item) {
    sendData(item["@controls"]["inlibris:delete"].href, item["@controls"]["inlibris:delete"].method, item, refreshPatron(item));
}

function appendLoanRow(body) {
    let link = "<a href='" +
            body["@controls"]["inlibris:target-book"].href +
            "' onClick='followLink(event, this, renderBook)'>" + body.book_barcode + "</a>";

    let renewLink = "Book late, cannot be renewed!";
    let status = body.status;

    $.ajax({
        url: body["@controls"]["inlibris:target-book"].href,
        success: function(data) {

            if (status === "Renewed") {
                status = status + " (" + body.renewed + "/" + data.renewlimit + ")";
            }

            let duedate = Date.parse(body.duedate);
            if (duedate > Date.now()) {
                renewLink = "<a href='" +
                        body["@controls"].self.href +
                        "' onClick='followLink(event, this, renewLoan)'>Renew</a>";
            }

            let returnLink = "<a href='" +
                    body["@controls"].self.href +
                    "' onClick='followLink(event, this, returnLoan)'>Return</a>";

            $(".secondresulttable tbody").append(
                "<tr><td>" + link +
                "</td><td>" + body.loandate +
                "</td><td>" + body.duedate +
                "</td><td>" + status +
                "</td><td>" + renewLink + "  |  " + returnLink + "</td></tr>"
            );
        },
        error: renderError
    });
}

function renderLoansBy(body) {
    let items = body.items;

    $(".secondtabletitle").html("<h3>Loans</h3>");
    if (items.length > 0) {
        $(".secondresulttable thead").html(
            "<tr><th>Barcode</th><th>Loan date</th><th>Due date</th><th>Status</th><th>Actions</th></tr>"
        );   
        $(".secondresulttable tbody").empty();
        items.forEach(function (item) {
            getResource(item["@controls"].self.href, appendLoanRow);
        });
    } else {
        $(".secondresulttable thead").html(
            "No loans"
        );
        $(".secondresulttable tbody").empty();
    }

}

function renderPatron(body) {
    current_book_object = null;
    current_patron_object = body;

    $("div.navigation").html(
        "<a href='" +
        body["@controls"].collection.href +
        "' onClick='followLink(event, this, renderPatrons)'> << Patrons</a>"
    );
    $(".firsttabletitle").html("<h3>Patron info</h3>");
    $(".firstresulttable thead").empty();
    $(".firstresulttable tbody").html(
        "<tr>" +
            "<th>Barcode</th>" +
            "<td>" + body.barcode + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>First name</th>" +
            "<td>" + body.firstname + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Last name</th>" +
            "<td>" + body.lastname + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Email</th>" +
            "<td>" + body.email + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Group</th>" +
            "<td>" + body.group + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Status</th>" +
            "<td>" + body.status + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Registration date</th>" +
            "<td>" + body.regdate + "</td>" +
        "</tr>"
    );
    getResource(body["@controls"]["inlibris:loans-by"].href, renderLoansBy);
}

function bookRow(item) {
    let link = "<a href='" +
            item["@controls"].self.href +
            "' onClick='followLink(event, this, renderBook)'>show</a>";

    return "<tr><td>" + item.barcode +
            "</td><td>" + item.author +
            "</td><td>" + item.title +
            "</td><td>" + link + "</td></tr>";
}

function renderLoanOf(item) {
    $(".secondtabletitle").html(
        "<h3>Loan status</h3>"
    );
    $(".secondresulttable thead").empty();
    $(".secondresulttable tbody").empty();
    $.ajax({
        url: item["@controls"]["inlibris:target-book"].href,
        success: function(data) {

            let status = item.status;
            if (status === "Renewed") {
                status = status + " (" + item.renewed + "/" + data.renewlimit + ")";
            }

            let link = "<a href='" +
                    item["@controls"].author.href +
                    "' onClick='followLink(event, this, renderPatron)'>" + item.patron_barcode + "</a>";


            $(".secondresulttable tbody").html(
                "<tr>" +
                    "<th>Status</th>" +
                    "<td>" + status + "</td>" +
                "</tr>" +
                "<tr>" +
                    "<th>Patron</th>" +
                    "<td>" + link + "</td>" +
                "</tr>" +
                "<tr>" +
                    "<th>Loan date</th>" +
                    "<td>" + item.loandate + "</td>" +
                "</tr>" +
                "<tr>" +
                    "<th>Due date</th>" +
                    "<td>" + item.duedate + "</td>" +
                "</tr>"
            );
        },
        error: renderError
    });
}

function refreshBook(data) {
    renderBook(current_book_object);
}

function createLoan(a) {
    $.ajax({
        url: $(a).attr("href"),
        book_barcode: current_book_object.barcode,
        success: function(data) {
            $.ajax({
                url: data["@controls"]["inlibris:loans-by"].href,
                success: function(data) {
                    let item = {"book_barcode": current_book_object.barcode};
                    sendData(
                        data["@controls"]["inlibris:add-loan"].href,
                        data["@controls"]["inlibris:add-loan"].method,
                        item,
                        refreshBook
                    );
                },
                error: renderError
            });
        },
        error: renderError
    });
}

function renderLoanPatronLink(item) {
    let link = "<a href='" +
            item["@controls"].self.href +
            "' onClick='event.preventDefault(); createLoan(this);'>" + item.barcode +
            " (" + item.lastname + ", " + item.firstname + ")" + "</a>";
    return "<td>" + link + "</td>";
}

function filterPatronsFunction() {
    /*
    Modified from https://www.w3schools.com/howto/howto_js_filter_lists.asp
    */
    var input = document.getElementById("patronSearch");
    var filter = input.value.toUpperCase();
    var filtered_patrons = [];
    var i, patron;

    var tbody = $(".secondresulttable tbody");
    tbody.empty();
    tbody.append("<br>");

    for (i = 0; i < all_patrons.length; i += 1) {
        patron = all_patrons[i];
        if (patron.barcode.toString().indexOf(filter) > -1) {
            filtered_patrons.push(patron);
        }
    }

    if (filtered_patrons.length > 10) {
        tbody.append("Too many results!");
    } else {
        for (i = 0; i < filtered_patrons.length; i += 1) {
            patron = filtered_patrons[i];
            tbody.append("<tr>");
            tbody.append(renderLoanPatronLink(patron));
            tbody.append("</tr>");
        }
    }
}

function renderLoanOfError(xhr, ajaxOptions, thrownError) {
    if (xhr.status === 400) {
        $(".secondtabletitle").html(
            "<h3>Loan status</h3>"
        );

        if (all_patrons === null) {
            $.ajax({
                url: current_book_object["@controls"].collection.href,
                success: function(data) {
                    $.ajax({
                        url: data["@controls"]["inlibris:patrons-all"].href,
                        book_barcode: current_book_object.barcode,
                        success: function(data) {
                            all_patrons = data.items;
                        },
                        error: renderError
                    });
                },
                error: renderError
            });
        }

        $(".secondresulttable thead").html(
            "Create a loan for: <input type='text' id='patronSearch' onkeyup='filterPatronsFunction()' placeholder='Enter patron barcode...'>"
        );
    }
}

function renderBook(body) {
    current_book_object = body;
    current_patron_object = null;

    $("div.navigation").html(
        "<a href='" +
        body["@controls"].collection.href +
        "' onClick='followLink(event, this, renderBooks)'> << Books</a>"
    );
    $(".firsttabletitle").html("<h3>Book info</h3>");
    $(".firstresulttable thead").empty()
    $(".firstresulttable tbody").html(
        "<tr>" +
            "<th>Barcode</th>" +
            "<td>" + body.barcode + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Title</th>" +
            "<td>" + body.title + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Author</th>" +
            "<td>" + body.author + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Publishing year</th>" +
            "<td>" + body.pubyear + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Format</th>" +
            "<td>" + body.format + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Description</th>" +
            "<td>" + body.description + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Loan time (days)</th>" +
            "<td>" + body.loantime + "</td>" +
        "</tr>" +
        "<tr>" +
            "<th>Renew limit</th>" +
            "<td>" + body.renewlimit + "</td>" +
        "</tr>"
    );

    $.ajax({
        url: body["@controls"]["inlibris:loan-of"].href,
        success: renderLoanOf,
        error: function(xhr, ajaxOptions, thrownError) {
            renderLoanOfError(xhr, ajaxOptions, thrownError);
        }
    });
}

function renderBooks(body) {
    current_book_object = null;
    current_patron_object = null;

    var items = body.items;
    items.sort(function(a, b) {
        return (a.barcode - b.barcode);
    });

    $("div.navigation").html(
        "<a href='" +
        body["@controls"]["inlibris:patrons-all"].href +
        "' onClick='followLink(event, this, renderPatrons)'>Patrons</a>"
        + " | " +
        "<a href='" +
        body["@controls"].self.href +
        "' onClick='followLink(event, this, renderBooks)'>Books</a>"
    );
    $(".firsttabletitle").html("<h3>Books</h3>");
    $(".firstresulttable thead").html(
        "<tr><th>Barcode</th><th>Author</th><th>Title</th><th>Actions</th></tr>"
    );   
    let tbody = $(".firstresulttable tbody");
    tbody.empty();
    items.forEach(function (item) {
        tbody.append(bookRow(item));
    });
    $("div.form").empty();
    emptySecondTable();
}

$(document).ready(function () {
    $("div.header").html(
        "<h1>Librarian Master UI</h1>"
    )

    getResource("http://localhost:5000/inlibris/api/", renderEntrypoint);
});
