# journal-flask

a minimal journaling web app.

you can post 1 entry per date. each entry can optionally have 1 image.

## first time setup & run dev server

create python virtual environment:
```
python3 -m venv my_env
```

activate environment:
```
source my_env/bin/activate
```

install dependencies:
```
pip install -r requirements.txt
```

choose a secure password and generate a hash for it by running this script:
```
python generate_password_hash.py
```

set environment variables (note - the hash needs to be inside single quotes):
```
export ADMIN_PASSWORD_HASH='pbkdf2:sha256:12345$abcedfg'
export SECRET_KEY=abcdef
```

initialize database:
```
python3 init_db.py
```

run app:
```
# optional
export FLASK_DEBUG=1

flask run
```

you can also edit config.yaml with your name and site title.

the username for logging in to the web app is 'admin' and the password is the one you created the hash for.

---

## subsequent dev server runs

activate environment:
```
source my_env/bin/activate
```

run app:
```
# optional
export FLASK_DEBUG=1

flask run
```

---

## run in prod

i am running my journal instance on a raspberry pi 400 running debian/raspbian.

this will vary depending on where you host it, but here are the steps i followed for my own reference:
- burn SD card image for the lastest raspbian (using raspberry pi imager). enabled SSH.
- booted up the pi plugged into ethernet.

i plan to serve it with nginx and gunicorn.

will put more notes here once i figure out the steps for that.

also need to set up backups for image files and database.