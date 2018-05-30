from django.shortcuts import render
from django.http import HttpResponse

from .forms import FeedbackForm

import requests
import os


TOKEN = "Token 2b92117b410cad8708fff3bfd7473340a69bfaac"  # Eliisan token
AUTH =  {'Authorization': TOKEN}

COURSE = 34      # summer en
EXERCISE = 5302  # melumittaus
BASE_URL = "https://plus.cs.tut.fi/api/v2/courses"


def index(request):
    url = f"{BASE_URL}/{COURSE}/submissiondata/?exercise_id={EXERCISE}&format=json"
    
    req = requests.get(url, headers=AUTH)
    subsdata = req.json()
    
    if "sub_files" not in os.listdir():
        os.mkdir("sub_files")
    
    for sub in subsdata:
        sub_url = sub["ohjelma.py"]
        req = requests.get(sub_url, headers=AUTH)
        req.encoding = "utf-8"
        filename = f"sub_files/{sub['SubmissionID']}.py"
        with open(filename, "w") as file:
            file.write(req.text)
    
    return render(request, "submissions/index.html", {"subs": subsdata})


def get_sub_info(request, sub_id):
    if request.method == "GET":
        sub_code = ""
        
        try:
            with open(f"sub_files/{sub_id}.py", "r") as file:
                sub_code = file.read()
                
        except Error as e:
            return HttpResponse(e)
            
        form = FeedbackForm()

    
    return render(request, "submissions/sub_code.html", {"sub_code": sub_code,
                                                         "form": form})
                                                         
