from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
#from cs50 import SQL
import sqlite3
import csv
import random
import base64

# Configure application
app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

"""Functions"""
def get_db():
    con = sqlite3.connect("photobox.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    return con, cur


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def error(reason="Please start again."):
    return render_template("error.html", reason=reason)

def convert_image_to_binary(picture):
    with open(picture, 'rb') as file:
        return file.read()


"""Routes"""
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    with open('static/art_quotes.csv', mode='r', encoding='utf-8') as quote_file:
        quote_reader = csv.reader(quote_file)
        quotes = list(quote_reader)
        random_quote = random.choice(quotes)
    return render_template("index.html", quote=random_quote[0])


@app.route("/login", methods=["GET","POST"])
def login():
    session.clear()
    if request.method == "POST":
        con, cur = get_db()
        if not request.form.get("username"):
            return error("No username entered")
        if not request.form.get("password"):
            return error("No password entered")
        rows = cur.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        user = rows.fetchall()
        con.close()
        if len(user) != 1 or not check_password_hash(user[0]["password"], request.form.get("password"),):
            return error("No user with inputed username and password")
        session["user_id"] = user[0]["id"]
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        con, cur = get_db()
        username = request.form.get("username")
        if not username:
            return error("please enter a name!")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not password or password != confirmation:
            return error("please enter a valid password!")
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?);", (username, generate_password_hash(password)))
            con.commit()
        except:
            con.close()
            return error("Username already taken")
        con.close()
        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if not request.files.get("picture"):
            return error("No picture uploaded.")
        picture = request.files.get("picture")
        con, cur = get_db()
        cur.execute("INSERT INTO photos(id, image) VALUES (?, ?)", (session["user_id"], picture.read()))
        con.commit()
        con.close()
        return redirect("/gallery")

    else:
        return render_template("upload.html")

@app.route("/gallery", methods=["GET", "POST"])
@login_required
def gallery():
    con, cur = get_db()
    if request.method == "POST":
        cur.execute("SELECT id FROM photos WHERE photo_id = ?", (request.form.get("photo_id"),))
        corresponding_id = cur.fetchone()
        if corresponding_id["id"] != session["user_id"]:
            con.close()
            return error("Not allowed!")
        cur.execute("SELECT is_public FROM photos WHERE photo_id = ?", (request.form.get("photo_id"),))
        current_publication_status = cur.fetchone()
        if current_publication_status["is_public"] == "no":
            cur.execute("UPDATE photos SET is_public = 'yes' WHERE photo_id = ?", (request.form.get("photo_id"),))
            con.commit()
        else:
            cur.execute("UPDATE photos SET is_public = 'no' WHERE photo_id = ?", (request.form.get("photo_id"),))
            con.commit()
        con.close()
        return redirect("/gallery")
    else:
        cur.execute("SELECT * FROM photos WHERE id = ? ORDER BY photo_id DESC", (session["user_id"],))
        photos =  cur.fetchall()
        photos = [dict(row) for row in photos]
        for entry in photos:
            entry["image"] = base64.b64encode(entry["image"]).decode("utf-8")
        con.close()
        return render_template("gallery.html", photos=photos)

@app.route("/posts")
@login_required
def posts():
    con, cur = get_db()
    cur.execute("SELECT username, image, date, time FROM photos JOIN users ON photos.id = users.id WHERE is_public = 'yes' ORDER BY photo_id DESC")
    photos = cur.fetchall()
    photos = [dict(row) for row in photos]
    for entry in photos:
        entry["image"] = base64.b64encode(entry["image"]).decode("utf-8")
    con.close()
    return render_template("posts.html", photos=photos)

@app.route("/delete", methods=["POST"])
@login_required
def delete():
    photo_id = request.form.get("photo_id")
    if not photo_id:
        return error("No existing photo with submitted id")
    con, cur = get_db()
    cur.execute("SELECT id FROM photos WHERE photo_id = ?", (photo_id,))
    corresponding_id = cur.fetchone()
    if corresponding_id["id"] != session["user_id"]:
            con.close()
            return error("Not allowed!")
    cur.execute("DELETE FROM photos WHERE photo_id = ?", (photo_id,))
    con.commit()
    con.close()
    return redirect("/gallery")

if __name__ == "__main__":
    app.run()