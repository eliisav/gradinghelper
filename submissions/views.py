from django.shortcuts import render
from django.http import HttpResponse
import requests


TOKEN = "Token 2b92117b410cad8708fff3bfd7473340a69bfaac"  # Eliisan token
AUTH =  {'Authorization': TOKEN}


EXERCISE_ID = 4565


def index(request):
    subs = []
    subs_url = f"https://plus.cs.tut.fi/api/v2/exercises/{EXERCISE_ID}/submissions/"
    
    while True:
        req = requests.get(subs_url, headers=AUTH)
        subs_json = req.json()
        
        for result in subs_json["results"]:
            subs.append(result)
        
        if not subs_json["next"]:
            break
        else:
            subs_url = subs_json["next"]

    return render(request, "submissions/index.html", {"subs": subs})

