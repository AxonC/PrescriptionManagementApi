# Prescription Service API
Advised to use `conda` to manage environments.

## Installation

Major Packages / Versions:
- Python 3.8
- FastApi
- Psypopg2 (Python PostgreSQL driver)

Dependencies can be installed using the following command:
```
pip install -f requirements.txt
```

## Running
Environment variables can be found in `config.py`. 

To run the API once installation complete:
```
uvicorn main:app --reload
```

To create a new user, import the `create_new_user` function from the `auth` module.
You should call this function with your username, name and plain password.
