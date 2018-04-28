# Python Flask application

This application runs the Flask instance that powers the web application.
It is currently missing the 'static' folder, as it contains many Node files, and Github doesn't want to take them all at once.

## Run the app locally

1. [Install Python][]
1. cd into this project's root directory
1. Run `pip install -r requirements.txt` to install the app's dependencies
1. Fill in the necessary information fields in `OpAware.py`, such as the SQL server and Slackbot keys and tokens.
1. Run `python OpAware.py`
1. Access the running app in a browser at <http://localhost:5000>

[Install Python]: https://www.python.org/downloads/
