from django.shortcuts import render
from django.http import HttpResponse
import requests


TOKEN = "Token 2b92117b410cad8708fff3bfd7473340a69bfaac"  # Eliisan token
AUTH =  {'Authorization': TOKEN}

COURSE = 34      # summer en
EXERCISE = 5302  # melumittaus
BASE_URL = "https://plus.cs.tut.fi/api/v2/courses"


def index(request):
    url = f"{BASE_URL}/{COURSE}/submissiondata/?exercise_id={EXERCISE}&format=json"
    
    req = requests.get(url, headers=AUTH)
    subsdata = req.json()
    
    return render(request, "submissions/index.html", {"subs": subsdata})

# Homma jatkuu...
# tee templateen linkki, josta voi avata opiskelijan koodin
# koodi pitänee hakea getillä täällä views-tiedoston puolella
# esitä koodi jotenkin jossain näkymässä
