## PWP SPRING 2020
# InLibris API

### Panu Mölsä solo project
<br/>

DL4: API implementation

File	Description
app.py	The main file, consisting of all the model and relationship definitions as well as some non-required API functions created only for personal testing and learning, will be probably scrapped when starting to actually the API
test.db	A populated database for testing
populate_db.py	A script for creating a populated database test.db
test_db.py	A pytest script for testing the database
requirements.txt	External Python libraries required to run the database


### Dependencies
* listed in "requirements.txt"

### Setting up the environment:
* Create a virtual environment in Python 3.7 and activate it (e.g. https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
* Clone this repository onto your computer
* Install dependencies from requirements.txt with command "pip install -r requirements.txt"
* Set the Flask app variable to "inlibris": In Windows "set FLASK_ENV=inlibris", in Linux "export FLASK_ENV=inlibris"
* Set the Flask enviromental variable to development: In Windows "set FLASK_ENV=development", in Linux "export FLASK_ENV=development"

### Setting up the database and running the API:

* Activate your virtual environment
* Run command "flask reset-db" to initialize and populate the database. This also resets the database back to its original state if it has been modified.
* If you want to test an empty database, run command "flask clear-db"
* To run the API, enter command "flask run"
* To enter the API, open URL "localhost:5000/inlibris/api/" in your browser

### Testing the API:

* Testing is provided for both the database and the API
* To run all tests, run command "pytest"
* To run all tests with coverage analysis, run command "pytest --conv=inlibris"
* To run the database tests, run command "pytest tests/db_test.py"
* To run the APItests, run command "pytest tests/api_test.py"
* Flask-SQLAlchemy raises a lot of deprecation warnings in Python 3.7. To silence them, you can use argument "-W ignore::DeprecationWarning" with all pytest commands

<br/><br/>
*Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint and instructions on how to setup and run the client*


