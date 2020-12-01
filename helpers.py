import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(titlepart):
    # Contact API
    try:
        api_key = '***REMOVED***'
        response = requests.get(f"https://www.omdbapi.com/?&apikey={api_key}&s={titlepart}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        movies = response.json()
        return movies['Search']

    except (KeyError, TypeError, ValueError):
        return None

def getdetails(imdbID):
    # Contact API
    try:
        api_key = '***REMOVED***'
        response = requests.get(f"https://www.omdbapi.com/?&apikey={api_key}&i={imdbID}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        movie = response.json()
        return movie
    except (KeyError, TypeError, ValueError):
        return None

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code
