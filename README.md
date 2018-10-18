# Grading Helper

Harjoitustehtävien arviointiprosessin hallintaan tarkoitettu työkalu, jota
voidaan käyttää yhdessä Aalto-yliopiston A+ -oppimisalustan kanssa
LTI-kirjautumisen kautta:
https://github.com/Aalto-LeTech/a-plus

## Getting Started

### Prerequisites
Python 3.6
pip

### Installing

Kloonaa repo esim.
```
git clone git@github.com:eliisav/gradinghelper.git
```

Luo ja aktivoi virtuaaliympäristö:
```
python3 -m venv ghelpervenv
source ghelpervenv/bin/activate
```

Asenna tarvittavat paketit:
```
pip install -r requirements.txt
```

### Local Settings

Projektihakemistoon tulee lisätä tiedosto local_settings.py, joka sisältää
vähintään seuraavat asetukset:

```
# Unique secret key for Djanog project
SECRET_KEY = 'abc123defg45hij678klm90nop'

# API token for A+ user. Needed to make API requests.
TOKEN = "Token abc123defg45hij678klm90nop"

# Database settings
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase',
    }
}
```

### LTI-login

LTI-kirjautumista varten tulee luoda tunnukset esim.

```
python3 manage.py add_lti_key
```

Luodut tunnukset sekä arviointityökalun kirjautumislinkki tulee lisätä
käytössä olevalle A+ -oppimisalustalle uutena LTI -palveluna.

### Crontab

Arviointityökalu ei hae harjoitustehtävien palautuksia automaattisesti.
Jos palautusten hakemisen haluaa automatisoida, niin sen voi tehdä crontabilla
kutsumalla management -komentoa update_submissions
