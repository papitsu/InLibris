So this is the database implementation for DL2

Database was implemented using Flask-SQLAlchemy with Python 3.7

Files:

| File | Description |
|:------: |:--------------:|
|**app.py** | The main file, consisting of all the model and relationship definitions as well as some non-required API functions created only for personal testing and learning, will be probably scrapped when starting to actually the API |
|**test.db** | A populated database for testing
|**populate_db.py** | A script for creating a populated database test.db
|**test_db.py** | A pytest script for testing the database
|**requirements.txt** | External Python libraries required to run the database

Dependencies (as listed in "requirements.txt")

*
*
*

Setting up the environment:

* Create a virtual environment in Python 3.7 and activate it (e.g. https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
* Install dependencies from requirements.txt with command "pip install -r requirements.txt"
* Set the Flask enviromental variable to development: In Windows "set FLASK_ENV=development", in Linux "export FLASK_ENV=development"

Setting up the database, populating it and running it:

* Clone this folder onto your computer
* Activate your virtual environment
* You can use the provided database dump "test.db"
* OR you can create a new database:
    * Delete the provided "test.db"
    * Create a new populated database: "python populate_db.py" (creates a database identical to the provided)
    
Testing the database:

* Once the database has been set up, run tests with command "pytest"
* Flask-SQLAlchemy raises a lot of deprecation warnings in Python 3.7. To silence them, you can use command "pytest -W ignore::DeprecationWarning"
