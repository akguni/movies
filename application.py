import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.secret_key = "dev"

# Configure CS50 Library to use SQLite database
db = SQL("postgres://***REMOVED***")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    #set iur api ke for the stock quote engine
    try:
        os.environ["API_KEY"] = "pk_a8ae175e4f5141629072dfcf092bc41a"
    except:
        raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    rows = db.execute("SELECT symbol, shares FROM stocks WHERE id = :id", id = session["user_id"])
    total = 0
    iexdata = {}

    for i in rows:
        iexdata[i["symbol"]] = lookup(i["symbol"])
        iexdata[i["symbol"]]["total"] = i["shares"] * iexdata[i["symbol"]]["price"]
        total += iexdata[i["symbol"]]["total"]
        iexdata[i["symbol"]]["total"] = usd(iexdata[i["symbol"]]["total"])
        iexdata[i["symbol"]]["price"] = usd(iexdata[i["symbol"]]["price"])

    cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])[0]["cash"]

    total += cash
    cash = usd(cash)
    total = usd(total)

    return render_template("index.html", rows=rows, iexdata=iexdata, cash=cash, total=total)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        if quote == None:
            return apology("This symbol does not exist", 403)

        else:
            row = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
            cash = row[0]["cash"]
            shares = float(request.form.get("shares"))
            price = quote["price"]
            cost = shares * price
            if cost > cash:
                flash("you do not have enough cash")
                return render_template("buy.html")

            else:
                cash -= cost
                db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash, id = session["user_id"])
                db.execute("INSERT INTO history (id, symbol, price, shares) VALUES (:id, :symbol, :price, :shares)", id = session["user_id"], symbol = symbol, price = price, shares = shares)
                row = db.execute("SELECT * FROM stocks WHERE id = :id AND symbol = :symbol", id = session["user_id"], symbol = symbol)

                if len(row) != 1:
                    db.execute("INSERT INTO stocks (id, symbol, shares) VALUES (:id, :symbol, :shares)", id = session["user_id"], symbol = symbol, shares = shares)

                else:
                    newshares = row[0]["shares"] + shares
                    db.execute("UPDATE stocks SET shares = :shares WHERE id = :id AND symbol = :symbol", shares = newshares, id = session["user_id"], symbol = symbol)

                flash('purchase complete')
                return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT * FROM history WHERE id = :id", id = session["user_id"])
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash('username cannot be left blank')
            return render_template("/login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('password cannot be left blank')
            return render_template("/login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash('invalid username and/or password')
            return render_template("/login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash('Logged in')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    """change password"""

    # User reached route via POST (as by submitting a form via POST)
    # Query database for username
    if request.method == "POST":

        rows = db.execute("SELECT hash FROM users WHERE id = :id", id=session["user_id"])
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash('current password is not correct')
            return render_template("/change.html")

        if request.form.get("new_password")!=request.form.get("confirm_password"):
            flash('passwords do not match')
            return render_template("/change.html")

        if request.form.get("password")==request.form.get("new_password"):
            flash('new password is identical to the old one')
            return redirect("/")

        hash = generate_password_hash(request.form.get("new_password"))
        db.execute("UPDATE users SET hash = :hash WHERE id = :id", hash=hash, id=session["user_id"])

        flash('password changed')
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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        quote=lookup(request.form.get("symbol"))
        if quote == None:
            flash("incorrect symbol")
            return render_template("quote.html")

        else:
            quote["price"] = usd(quote["price"])
            return render_template("quoted.html", quote=quote)
    else:
        return render_template("quote.html")


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
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        # Ensure username does not exist
        if len(rows) != 0:
            flash('user already exists')
            return render_template("register.html")

        hash = generate_password_hash(request.form.get("password"))

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=hash)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    symbols = db.execute("SELECT symbol FROM stocks WHERE id = :id", id = session["user_id"])
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = float(request.form.get("shares"))
        stock = db.execute("SELECT shares FROM stocks WHERE id = :id AND symbol = :symbol", id=session["user_id"], symbol=symbol)
        if shares > stock[0]["shares"]:
            flash('that is more than you own')
            return render_template("sell.html", symbols=symbols)

        else:
            quote = lookup(symbol)
            price = quote["price"]
            revenue = shares * price
            row = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
            cash = row[0]["cash"]
            cash += revenue
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash, id = session["user_id"])
            newshares = stock[0]["shares"] - shares
            db.execute("UPDATE stocks SET shares = :shares WHERE id = :id AND symbol = :symbol", shares = newshares, id = session["user_id"], symbol = symbol)
            db.execute("INSERT INTO history (id, symbol, price, shares) VALUES (:id, :symbol, :price, :shares)", id = session["user_id"], symbol = symbol, price = price, shares = -shares)

            flash('sale complete')
            return redirect("/")

    else:
        return render_template("sell.html", symbols=symbols)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
