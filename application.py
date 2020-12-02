import os

from cs50 import SQL
import psycopg2
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from sqlalchemy import create_engine

#from flask_session import Session
#from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, getdetails

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# This is for session management
app.secret_key ='***REMOVED***'

# Access postgres database
# use either production or local from one of the two below but not both
# This one is for production on heroku servers
db = create_engine('postgresql+psycopg2://***REMOVED***')
# This one is for local postgres file
# db = create_engine('postgresql+psycopg2://ismas:postgres@localhost:5432/movies')

# Make sure API key is set
if not os.environ.get("API_KEY"):
    #Set API Key for OMDB
    try:
        os.environ["API_KEY"] = "***REMOVED***"
    except:
        raise RuntimeError("API_KEY not set")

# Global variables
keys = ['Title', 'Year', 'Genre', 'Director',  'Actors', 'Plot', 'imdbRating', 'Poster', 'imdbID']
statskey = ['Listed', 'Watched', 'Watchlist', 'Best', 'Rated', 'avg_rating']
scale = ['None', 'Awful', 'Bad', 'OK', 'Good', 'Excellent']
allmovies = [[0 for x in range(9)] for y in range(2)]
categories = (db.engine.execute("SELECT * FROM special_categories ORDER BY category_id").fetchall())

# Start Page    
@app.route("/")
@login_required
def index():
    return redirect("/lists")

# Page to search and add movies to lists
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":
        movies=lookup(request.form.get("titlepart"))
        if movies == None:
            flash("Could not find any movies with that word. Please try again.")
            return render_template("search.html")

        else:            
            return render_template("found.html", movies=movies)
    else:
        return render_template("search.html")

# Display details of the selected movie and action
@app.route('/details/<imdbID>')
@login_required
def details(imdbID):
    movie = getdetails(imdbID)
    this_movie = {"listed": "", "watched": "", "watchlist": "", "rating": ["checked","","","","",""], "special_category": ["selected","","","",""]}
    exists = db.engine.execute("SELECT * FROM user_list WHERE imdbid = %s AND id = %s", (movie["imdbID"], session["user_id"])).fetchall()
    if len(exists) == 1:
        this_movie["listed"] = "checked"
        if (exists[0][3]):
            this_movie["watched"] = "checked"
        if (exists[0][4] != None and exists[0][4] != 0):
            this_movie["rating"][0]=""
            this_movie["rating"][exists[0][4]] = "selected"
        if (exists[0][5]!= None and exists[0][5] != 0):
            this_movie["special_category"][0]=""
            this_movie["special_category"][exists[0][5]] = "selected"
        if (exists[0][6]):
            this_movie["watchlist"] = "checked"

    moviestats = db.engine.execute("SELECT listed, watched, watchlist, best, rated, sum_rating FROM movies WHERE imdbid = %s", (imdbID,)).fetchall()

    if len(moviestats) != 1:
        listed = watched = watchlist = best = rated = avg_rating = 0
    else:
        moviestats = moviestats[0]
        listed, watched, watchlist, best, rated = moviestats[0], moviestats[1], moviestats[2], moviestats[3], (moviestats[4] or 0)
        if rated == 0:
            avg_rating = rated
        else:
            avg_rating = round(moviestats[5] / rated)

    this_movie_stats = [listed, watched, watchlist, best, rated, avg_rating]            

    return render_template("details.html", movie=movie, this_movie=this_movie, keys=keys, categories=categories, this_movie_stats=this_movie_stats, statskey=statskey, scale=scale)


# Add movie (and rating) to user list
@app.route("/save", methods=["POST"])
@login_required
def save():
    if request.method == "POST":
        imdbID = request.form.get("imdbID")
        Title = request.form.get("Title")
        Year = request.form.get("Year")
        Genre = request.form.get("Genre")
        Director = request.form.get("Director")
        Actors = request.form.get("Actors")
        Plot = request.form.get("Plot")
        imdbRating = request.form.get("imdbRating")
        Poster = request.form.get("Poster")
        
        watchlist = False
        if request.form.get("watched") == "true":
            watched = True
        else:
            watched = False
            if request.form.get("watchlist") == "true":
                watchlist = True

        rating = int(request.form.get("own_rating") or 0)
        special_category =  int(request.form.get("special_category") or 0)
        save_message = 'Changes saved to your lists.'
        # check if the movie is already in the database
        moviedb = db.engine.execute("SELECT * FROM movies WHERE imdbid = %s", (imdbID)).fetchall()
        # record properties before changes for comparison
        before = (db.engine.execute("SELECT * FROM user_list WHERE imdbid = %s AND id = %s", (imdbID, session["user_id"])).fetchall())
        # remaining allocations for the requested 'best of' category
        contingent = (db.engine.execute("SELECT max FROM special_categories WHERE category_id = %s", (special_category,)).fetchall())[0][0]-(db.engine.execute("SELECT COUNT (*) FROM user_list WHERE id = %s AND special_category = %s", (session["user_id"], special_category)).fetchall())[0][0]
        # Does the current user already have this movie in their list?
        if len(before) == 1:
            before = before[0]
            # and the user cleared the listed checkbox, then delete it
            if request.form.get("listed") != "true":
                db.engine.execute("DELETE FROM user_list WHERE imdbid = %s AND id = %s", (imdbID, session["user_id"]))
                #decrement the user listed number
                db.engine.execute("UPDATE users SET listed = listed - 1 WHERE id = %s", (session["user_id"],))
                if before[3]:
                    db.engine.execute("UPDATE users SET watched = watched - 1 WHERE id = %s", (session["user_id"],))
                if before[4] > 0:
                    db.engine.execute("UPDATE users SET rated = rated - 1 WHERE id = %s", (session["user_id"],))
                if before[5] > 0:
                    db.engine.execute("UPDATE users SET best = best - 1 WHERE id = %s", (session["user_id"],))
                if before[6]:
                    db.engine.execute("UPDATE users SET watchlist = watchlist - 1 WHERE id = %s", (session["user_id"],))

                # if there are no other users who have this movie in their list, then delete it from the local database
                exists = db.engine.execute("SELECT DISTINCT imdbid FROM user_list WHERE imdbid = %s", (imdbID,)).fetchall()
                if len(exists) != 1:
                    db.engine.execute("DELETE FROM movies WHERE imdbid = %s", (imdbID,))
                # otherwise decrement the properties from movies table
                else:
                    db.engine.execute("UPDATE movies SET listed = listed - 1 WHERE imdbid = %s", (imdbID,))
                    if before[3]:
                        db.engine.execute("UPDATE movies SET watched = watched - 1 WHERE imdbid = %s", (imdbID,))
                    if before[4] > 0:
                        db.engine.execute("UPDATE movies SET rated = rated - 1, sum_rating = (sum_rating - %s) WHERE imdbid = %s", (before[4], imdbID))
                    if before[5] > 0:
                        db.engine.execute("UPDATE movies SET best = best - 1 WHERE imdbid = %s", (imdbID,))
                    if before[6]:
                        db.engine.execute("UPDATE movies SET watchlist = watchlist - 1 WHERE imdbid = %s", (imdbID,))
           
            # The user has this in their list and wants to keep it, so update properties by comparing to status before
            else:
                if (watched and not before[3]):
                    db.engine.execute("UPDATE movies SET watched = watched + 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                    db.engine.execute("UPDATE users SET watched = watched + 1 WHERE id = %s", (session["user_id"],))
                
                elif (not watched and before[3]):
                    db.engine.execute("UPDATE movies SET watched = watched - 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                    db.engine.execute("UPDATE users SET watched = watched - 1 WHERE id = %s", (session["user_id"],))
                
                if (watchlist and not before[6]):
                    db.engine.execute("UPDATE movies SET watchlist = watchlist + 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                    db.engine.execute("UPDATE users SET watchlist = watchlist + 1 WHERE id = %s", (session["user_id"],))
                
                elif (not watchlist and before[6]):
                    db.engine.execute("UPDATE movies SET watchlist = watchlist - 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                    db.engine.execute("UPDATE users SET watchlist = watchlist - 1 WHERE id = %s", (session["user_id"],))

                if (rating != before[4]):
                    db.engine.execute("UPDATE movies SET sum_rating = sum_rating + %s, last_save = now(), last_editor = %s WHERE imdbid = %s", ((rating - before[4]), session["user_id"], imdbID))

                    if before[4] < 1:                        
                        db.engine.execute("UPDATE movies SET rated = rated + 1, last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                        db.engine.execute("UPDATE users SET rated = rated + 1 WHERE id = %s", (session["user_id"],))

                    if rating == 0:
                        db.engine.execute("UPDATE movies SET rated = rated - 1, last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                        db.engine.execute("UPDATE users SET rated = rated - 1 WHERE id = %s", (session["user_id"],))

                if (special_category != before[5]):
                    if special_category == 0:
                        db.engine.execute("UPDATE movies SET best = best - 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                        db.engine.execute("UPDATE users SET best = best - 1 WHERE id = %s", (session["user_id"],))
                
                    elif contingent > 0:
                        if before[5] == 0:
                            db.engine.execute("UPDATE movies SET best = best + 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                            db.engine.execute("UPDATE users SET best = best + 1 WHERE id = %s", (session["user_id"],))
                    else:
                        special_category = before[5]
                        save_message = "You have already allocated maximum number of movies under that 'best' category. If you still want to give this category to this movie, please first remove this category from one or more other movie. All other changes are saved."

                db.engine.execute("UPDATE user_list SET save_date = now(), user_watched = %s, user_rating = %s, special_category = %s, user_watchlist = %s WHERE id = %s AND imdbID = %s", (watched, rating, special_category, watchlist, session["user_id"], imdbID))

        else:
            # The user does not have this movie in their list yet
            if len(moviedb) != 1:
                # If the movie is not yet in local database
                # insert it into local db

                db.engine.execute("INSERT INTO movies (imdbid, title, year, genre, director, actors, plot, imdbrating, poster, last_editor) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (imdbID, Title, Year, Genre, Director, Actors, Plot, imdbRating, Poster, session["user_id"]))

            if contingent <= 0:
                special_category = 0
                save_message = "You have already allocated maximum number of movies under that 'best' category. If you still want to give this category to this movie, please first remove this category from one or more other movie. All other changes are saved."

            # add the movie in users list
            db.engine.execute("INSERT INTO user_list (id, imdbID, user_watched, user_rating, special_category, user_watchlist) VALUES (%s, %s, %s, %s, %s, %s)", (session["user_id"], imdbID, watched, rating, special_category, watchlist))

            # increment the properties in movies and users tables as necessary
            db.engine.execute("UPDATE users SET listed = listed + 1 WHERE id = %s", (session["user_id"],))
            
            db.engine.execute("UPDATE movies SET listed = listed + 1 WHERE imdbid = %s", (imdbID,))
            if watched:
                db.engine.execute("UPDATE movies SET watched = watched + 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                db.engine.execute("UPDATE users SET watched = watched + 1 WHERE id = %s", (session["user_id"],))
                if rating > 0:
                    db.engine.execute("UPDATE movies SET rated = rated + 1, last_save = now(), last_editor = %s, sum_rating = sum_rating + %s WHERE imdbid = %s", (session["user_id"], rating, imdbID))
                    db.engine.execute("UPDATE users SET rated = rated + 1 WHERE id = %s", (session["user_id"],))

                if special_category > 0:
                    db.engine.execute("UPDATE movies SET best = best + 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                    db.engine.execute("UPDATE users SET best = best + 1 WHERE id = %s", (session["user_id"],))

            elif watchlist:
                db.engine.execute("UPDATE movies SET watchlist = watchlist + 1, last_save = now(), last_editor = %s WHERE imdbid = %s", (session["user_id"], imdbID))
                db.engine.execute("UPDATE users SET watchlist = watchlist + 1 WHERE id = %s", (session["user_id"],))            

        flash(save_message)
        return redirect ("/lists")

# To show the list of movies users saved and their ratings etc
@app.route("/lists", methods=["GET", "POST"])
@login_required
def lists():
   
    allmovies[0][0] = (db.engine.execute("SELECT COUNT (*) FROM user_list WHERE id = %s", (session["user_id"]),).fetchone())[0]
    allmovies[0][1] = (db.engine.execute("SELECT COUNT (*) FROM user_list WHERE id = %s AND user_watched = %s", (session["user_id"], True),).fetchone())[0]
    allmovies[0][2] = (db.engine.execute("SELECT COUNT (*) FROM user_list WHERE id = %s AND user_watchlist = %s", (session["user_id"], True),).fetchone())[0]
    allmovies[0][3] = (db.engine.execute("SELECT COUNT (imdbid) FROM user_list WHERE id = %s AND user_rating > 0", (session["user_id"],),).fetchone())[0]
    allmovies[0][4] = (db.engine.execute("SELECT COUNT (imdbid) FROM user_list WHERE id = %s AND special_category > 0", (session["user_id"],),).fetchone())[0]
    for i in range(1, 5):
        allmovies[0][i+4] = (db.engine.execute("SELECT COUNT (DISTINCT imdbid) FROM user_list WHERE id = %s AND special_category = %s", (session["user_id"], i)).fetchone())[0]
    allmovies[1][0] = (db.engine.execute("SELECT COUNT (DISTINCT imdbid) FROM user_list").fetchone())[0]
    allmovies[1][1] = (db.engine.execute("SELECT COUNT (DISTINCT imdbid) FROM user_list WHERE user_watched = %s", (True,)).fetchone())[0]
    allmovies[1][2] = (db.engine.execute("SELECT COUNT (DISTINCT imdbid) FROM user_list WHERE user_watchlist = %s", (True),).fetchone())[0]
    allmovies[1][3] = (db.engine.execute("SELECT COUNT (DISTINCT imdbid) FROM user_list WHERE user_rating > 0").fetchone())[0]
    allmovies[1][4] = (db.engine.execute("SELECT COUNT (DISTINCT imdbid) FROM user_list WHERE special_category > 0").fetchone())[0]
    for i in range(1, 5):
        allmovies[1][i+4] = (db.engine.execute("SELECT COUNT (DISTINCT imdbid) FROM user_list WHERE special_category = %s", (i,)).fetchone())[0]
    
    return render_template("lists.html", allmovies=allmovies, categories=categories)

@app.route('/drilldown/<choice>')
@login_required
def drilldown(choice):

    if choice == "00":
        list = (db.engine.execute("SELECT * FROM movies JOIN user_list ON movies.imdbid=user_list.imdbid WHERE user_list.id = %s ORDER BY save_date DESC", (session["user_id"]),).fetchall())
        report = "saved by me"
    elif choice == "01":
        list = (db.engine.execute("SELECT * FROM movies JOIN user_list ON movies.imdbid=user_list.imdbid WHERE user_list.id = %s AND user_watched = True ORDER BY save_date DESC", (session["user_id"],),).fetchall())
        report = "watched by me"
    elif choice == "02":
        list = (db.engine.execute("SELECT * FROM movies JOIN user_list ON movies.imdbid=user_list.imdbid WHERE user_list.id = %s AND user_watchlist = True ORDER BY save_date DESC", (session["user_id"],),).fetchall())
        report = "watchlisted by me"
    elif choice == "03":
        list = (db.engine.execute("SELECT * FROM movies JOIN user_list ON movies.imdbid=user_list.imdbid WHERE user_list.id = %s AND user_rating > 0 ORDER BY last_save DESC", (session["user_id"],),).fetchall())
        report = "rated by me"
    elif choice == "04":
        list = (db.engine.execute("SELECT * FROM movies JOIN user_list ON movies.imdbid=user_list.imdbid WHERE user_list.id = %s AND special_category > 0 ORDER BY last_save DESC", (session["user_id"],),).fetchall())
        report = "categorized 'best' by me"
    else:
        for i in range(1, 5):
            if choice == "0"+str(i+4):
                list = (db.engine.execute("SELECT * FROM movies JOIN user_list ON movies.imdbid=user_list.imdbid WHERE user_list.id = %s AND special_category = %s ORDER BY last_save DESC", (session["user_id"], i)).fetchall())
                report = "categorized 'Best of "+categories[i][1]+"' by me"
                break
        
    if choice == "10":
        list = (db.engine.execute("SELECT * FROM movies WHERE imdbid IN (SELECT imdbid FROM user_list) ORDER BY last_save DESC").fetchall())
        report = "saved by all users"
    elif choice == "11":
        list = (db.engine.execute("SELECT * FROM movies WHERE imdbid IN (SELECT imdbid FROM user_list WHERE user_watched = True) ORDER BY last_save DESC").fetchall())
        report = "watched by all users"
    elif choice == "12":
        list = (db.engine.execute("SELECT * FROM movies WHERE imdbid IN (SELECT imdbid FROM user_list WHERE user_watchlist = True) ORDER BY last_save DESC").fetchall())
        report = "watchlisted by all users"
    elif choice == "13":
        list = (db.engine.execute("SELECT * FROM movies WHERE imdbid IN (SELECT imdbid FROM user_list WHERE user_rating > 0) ORDER BY last_save DESC").fetchall())
        report = "rated by all users"
    elif choice == "14":
        list = (db.engine.execute("SELECT * FROM movies WHERE imdbid IN (SELECT imdbid FROM user_list WHERE special_category > 0) ORDER BY last_save DESC").fetchall())
        report = "categorized 'best' by all users"
    else:
        for i in range(1, 5):
            if choice == "1"+str(i+4):
                list = (db.engine.execute("SELECT * FROM movies WHERE imdbid IN (SELECT imdbid FROM user_list WHERE special_category = %s) ORDER BY last_save DESC", (i,)).fetchall())
                report = "categorized 'Best of "+categories[i][1]+"' by all users"
                break

    return render_template("drilldown.html", report=report, list=list)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash('Username cannot be left blank. Please try again.')
            return render_template("/login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('Password cannot be left blank. Please try again.')
            return render_template("/login.html")

        # Query database for username
        rows = db.engine.execute("SELECT * FROM users WHERE username = %s", (request.form.get("username"),)).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash('Invalid username and/or password. Please try again.')
            return render_template("/login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["user_name"] = rows[0]["username"]

        # Redirect user to home page
        flash('Login successful.')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Please provide a username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Please provide a password", 403)
        # Ensure passwords are identical
        elif request.form.get("password")!=request.form.get("confirm_password"):
            flash('passwords do not match')
            return render_template("register.html")

        # Query database for username
        username=request.form.get("username")
        rows = db.engine.execute("SELECT * FROM users WHERE username = %s", (username,)).fetchall()
        # Ensure username does not exist
        if len(rows) != 0:
            flash('This user already exists. Please try again.')
            return render_template("register.html")

        hash = generate_password_hash(request.form.get("password"))

        db.engine.execute("INSERT INTO users (username, hash) VALUES (%s, %s)", (username, hash))

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
    # Query database for username
        rows = db.execute("SELECT hash FROM users WHERE id = %s", (session["user_id"],)).fetchall()
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash('Current password is not correct. Please try again.')
            return render_template("/change.html")

        if request.form.get("new_password")!=request.form.get("confirm_password"):
            flash('passwords do not match')
            return render_template("/change.html")

        if request.form.get("password")==request.form.get("new_password"):
            flash('New password is identical to the old one. Please try again.')
            return redirect("/")

        hash = generate_password_hash(request.form.get("new_password"))
        db.execute("UPDATE users SET hash = %s WHERE id = %s", (hash, session["user_id"]))

        flash('Password changed.')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")        

# Error handling code

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)