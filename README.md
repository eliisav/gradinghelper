# Grading Helper

Harjoitustehtävien arviointiprosessin hallintaan tarkoitettu työkalu, jota
voidaan käyttää yhdessä Aalto-yliopiston A+ -oppimisalustan kanssa
LTI-kirjautumisen kautta:
https://github.com/Aalto-LeTech/a-plus

## Getting Started

### Prerequisites
Vähintään Python 3.6, pip

### Installing

Kloonaa repo, esim:
```
git clone git@github.com:eliisav/gradinghelper.git
```

Luo ja aktivoi virtuaaliympäristö, esim:
```
python3 -m venv ghelpervenv
source ghelpervenv/bin/activate
```

Asenna tarvittavat paketit:
```
pip install -r requirements.txt
```

### Local Settings

Projektihakemistoon tulee lisätä tiedosto local_settings.py, jossa
määritellään ```SECRET_KEY``` ja ```DATABASES```. Esim:

```
# Unique secret key for Django project
SECRET_KEY = 'abc123defg45hij678klm90nop'

# Database settings
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase',
    }
}
```

Tarpeen mukaan voidaan määritellä myös ```LOGGING```.

Tuotantoa varten tulee edellisten lisäksi määritellä ```ALLOWED_HOSTS```
ja asettaa ```DEBUG = False```.

### Migraatiot

```
python3 manage.py migrate
```

### LTI-login

LTI-kirjautumista varten tulee luoda tunnukset esim.

```
python3 manage.py add_lti_key -d "my_lms"
```

Luodut tunnukset sekä arviointityökalun kirjautumislinkki tulee lisätä
käytössä olevalle A+ -oppimisalustalle uutena LTI -palveluna.

### Custom management commands for crontab
Updating some course details, exercises and submissions can be automated with 
crontab.
#### update_submissions
If it's needed to poll new submissions freaquently, create a cronjob to call the
management function ```update_submissions```.
#### update_courses
This function updates some course details and exercise list.