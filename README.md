# journal-flask

a minimal journaling web app.

view my instance here: [journal.palomakop.tv](https://journal.palomakop.tv)

you can post 1 entry per date.

features:
- super simple (brutalist?) and mobile-friendly interface
- full text rss feed
- follows [html journal spec](https://journal.miso.town/)
- posts can have images, images are optimized but you can view full size by clicking them, also you can add alt text
- you can use markdown in posts for formatting
- open source, feel free to run your own / fork and customize

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

edit config.yaml with your name and site title, and edit about.html to customize the about page. you will need to fork the repo to do that for now since those files are currently tracked in git.

replace /static/default-og-image.jpg with your own preview image

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

this will vary depending on where you host it, but here are the steps i followed:
- burn SD card image for the lastest raspbian (using raspberry pi imager) - bookworm
- booted up the pi plugged into ethernet
- SSH'd in and updated packages
- git cloned the repo
- followed steps above for initial setup
- installed and started redis ([reference](https://pimylifeup.com/raspberry-pi-redis/))
    - note: got an error when trying to enable redis.service via the symlink so i had to run `sudo systemctl enable /lib/systemd/system/redis-server.service`
- added `export REDIS_URL=redis://localhost:6379` to environment vars
- installed nginx, certbot, and ufw
    - sort of followed [this tutorial](https://medium.com/@kawsarlog/from-flask-to-live-deploying-your-app-with-nginx-gunicorn-ssl-and-custom-domain-1e8b57709fc0) to set up nginx and gunicorn to serve the app
- started nginx
- set up https with let's encrypt
- set up port forwarding on my router to forward 80 and 443 to my pi
- created an A DNS record pointing to my home network IPv4 address (we have a static ip already)
- activated the python virtual environment and installed gunicorn and redis
- set up a systemctl service for gunicorn

to do:
- set up backups for image files and database