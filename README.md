## PWP SPRING 2020
# InLibris API

### Panu Mölsä solo project
<br/>

## DL4: API implementation

Finished 3.4.2020.

### Dependencies
* listed in "requirements.txt"

### Setting up the environment:
* Create a virtual environment in Python 3.7 and activate it (e.g. https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
* Clone this repository onto your computer
* Install project and dependencies with command "pip install -e inlibris" from the folder which contains the repository folder
* Set the Flask app variable to "inlibris": In Windows "set FLASK_APP=inlibris", in Linux "export FLASK_APP=inlibris"
* Set the Flask enviromental variable to development: In Windows "set FLASK_ENV=development", in Linux "export FLASK_ENV=development"

### Setting up the database and running the API:

* Activate your virtual environment
* Run command "flask reset-db" to initialize and populate the database. This also resets the database back to its original state if it has been modified.
* If you want to test an empty database, run command "flask clear-db"
* To run the API, enter command "flask run"
* To access the API, open the entry point URL "localhost:5000/inlibris/api/" in your browser
* The API can be further explored using the URLs in the hypermedia controls

### Testing the API:

* Testing is provided for both the database and the API
* Flask-SQLAlchemy raises a lot of deprecation warnings in Python 3.7. To silence them, you can use argument "-W ignore::DeprecationWarning" with all following pytest commands
* To run all tests, run command "pytest"
* To run all tests with coverage analysis, run command "pytest --conv=inlibris"
* To run the database tests, run command "pytest tests/db_test.py"
* To run the APItests, run command "pytest tests/api_test.py"

I wrote the tests quite early on in the API development which helped me catch errors quickly and just monitor if any new implementations broke the API. Some main errors I detected only thanks to the functional testing were my conflict cases in the PUT methods. While the API seemed to work fine and return quite coherent error status codes, the tests quickly informed me that the conflict cases and 404 errors were not actually detecting the correct mistakes in the requests.

## DL5: Client design and implementation

Finished 24.4.2020.

### Running the client

Once the database and API are running, the client can be accessed by opening "localhost:5000/inlibris/librarian/" in your browser.

Client uses six resources from the API. It uses methods GET, PUT, POST and DELETE. It doesn't use any additional APIs. No testing is implemented for the client. The client is a true hypermedia client: only the entrypoint URL is specified and all the other requests are formed using the hypermedia links.

<br/><br/>
*Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint and instructions on how to setup and run the client*


