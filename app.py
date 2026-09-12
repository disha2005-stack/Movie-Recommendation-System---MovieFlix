# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import json
import os

from data.recommender import (
    recommend,
    personalized_recommend,
    filter_movies,
    get_movie_details,
    get_local_movie_details,
    get_all_titles
)


USERS_FILE = "users.json"


# ---------------- LOAD USERS ----------------

def load_users():

    if not os.path.exists(USERS_FILE):
        return {"users": []}

    with open(USERS_FILE, "r") as file:
        return json.load(file)


# ---------------- SAVE USERS ----------------

def save_users(data):

    with open(USERS_FILE, "w") as file:
        json.dump(data, file, indent=4)


# ---------------- BUILD MOVIE CARDS ----------------

def build_movie_cards(movie_titles, use_external_details=True):

    movies = []

    for movie in movie_titles:

        local_details = get_local_movie_details(movie)
        external_details = (
            get_movie_details(movie)
            if use_external_details
            else {}
        )

        details = {
            key: value if value not in (None, "", "N/A") else local_details[key]
            for key, value in external_details.items()
        }

        for key, value in local_details.items():
            details.setdefault(key, value)

        movies.append({
            "title": movie,
            "poster": details["poster"],
            "rating": details["rating"],
            "genre": details["genre"],
            "year": details["year"]
        })

    return movies


# ---------------- FLASK APP ----------------

app = Flask(__name__)

app.secret_key = "supersecretkey"


# ---------------- HOME ----------------

DEFAULT_TRENDING = [
    "Toy Story (1995)", "Heat (1995)", "GoldenEye (1995)", "Casino (1995)",
    "Braveheart (1995)", "Apollo 13 (1995)", "Jumanji (1995)", "Pulp Fiction (1994)"
]

DEFAULT_POPULAR = [
    "Star Wars: Episode IV - A New Hope (1977)", "Forrest Gump (1994)", "Matrix, The (1999)",
    "Jurassic Park (1993)", "Shawshank Redemption, The (1994)", "Fight Club (1999)"
]

DEFAULT_TOP_RATED = [
    "Godfather, The (1972)", "Schindler's List (1993)", "Usual Suspects, The (1995)",
    "Silence of the Lambs, The (1991)", "Fargo (1996)", "Goodfellas (1990)"
]


@app.route("/")
def home():

    matched_title = session.get("matched_title")
    recommendations = session.get("recommendations", [])

    personalized_movies = []

    if "user" in session:

        username = session["user"]
        data = load_users()

        for user in data["users"]:

            if user["username"] == username:

                favorites = user.get("favorites", [])
                watch_later = user.get("watch_later", [])
                ratings = user.get("ratings", {})
                watched = user.get("watched", [])

                break

        else:

            favorites = []
            watch_later = []
            ratings = {}
            watched = []

        personalized_titles = personalized_recommend(
            favorites,
            watch_later,
            ratings,
            watched
        )

        personalized_movies = build_movie_cards(
            personalized_titles,
            use_external_details=False
        )

    trending_movies = build_movie_cards(DEFAULT_TRENDING, use_external_details=False)
    popular_movies = build_movie_cards(DEFAULT_POPULAR, use_external_details=False)
    top_rated_movies = build_movie_cards(DEFAULT_TOP_RATED, use_external_details=False)

    return render_template(
        "index.html",
        matched_title=matched_title,
        recommendations=recommendations,
        personalized_movies=personalized_movies,
        trending_movies=trending_movies,
        popular_movies=popular_movies,
        top_rated_movies=top_rated_movies,
        filtered_movies=[]
    )


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        data = load_users()

        # Check if user already exists

        for user in data["users"]:

            if user["email"] == email:

                return "User already exists"

        # Hash password

        hashed_password = generate_password_hash(password)

        # Create new user

        new_user = {

            "username": username,

            "email": email,

            "password": hashed_password,

            "favorites": [],

            "watch_later": [],

            "watched": [],

            "ratings": {}

        }

        data["users"].append(new_user)

        save_users(data)

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        data = load_users()

        user = None

        for u in data["users"]:

            if u["email"] == email:

                user = u

                break

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user"] = user["username"]

            return redirect(url_for("home"))

        return "Invalid email or password"

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect(url_for("login"))


# ---------------- GET ALL MOVIE TITLES ----------------

@app.route("/titles")
def titles():

    return get_all_titles()


# ---------------- MOVIE RECOMMENDATION ----------------

@app.route("/recommend", methods=["POST"])
def get_recommendations():

    movie_name = request.form["movie_name"]

    result = recommend(movie_name)

    if result:

        matched_title, recommendations = result

        movies_with_details = []

        for movie in recommendations:

            details = get_movie_details(movie)

            movies_with_details.append({

                "title": movie,

                "poster": details["poster"],

                "rating": details["rating"],

                "genre": details["genre"],

                "year": details["year"]

            })

    else:

        matched_title = None

        movies_with_details = []

    session["matched_title"] = matched_title

    session["recommendations"] = movies_with_details

    return redirect(url_for("home"))


# ---------------- ADD FAVORITE ----------------

@app.route("/favorite", methods=["POST"])
def favorite():

    if "user" not in session:

        return redirect(url_for("login"))

    movie = request.form["movie"]

    username = session["user"]

    data = load_users()

    for user in data["users"]:

        if user["username"] == username:

            if "favorites" not in user:

                user["favorites"] = []

            if movie not in user["favorites"]:

                user["favorites"].append(movie)

            break

    save_users(data)

    return redirect(url_for("favorites_page"))


# ---------------- FAVORITES PAGE ----------------

@app.route("/favorites")
def favorites_page():

    if "user" not in session:

        return redirect(url_for("login"))

    username = session["user"]

    data = load_users()

    favorites = []

    for user in data["users"]:

        if user["username"] == username:

            favorites = user.get(
                "favorites",
                []
            )

            break

    return render_template(
        "favorites.html",
        favorites=build_movie_cards(favorites, use_external_details=False)
    )


# ---------------- REMOVE FAVORITE ----------------

@app.route("/remove_favorite/<path:movie_title>", methods=["POST"])
def remove_favorite(movie_title):

    if "user" not in session:

        return redirect(url_for("login"))

    username = session["user"]

    data = load_users()

    for user in data["users"]:

        if user["username"] == username:

            if "favorites" not in user:

                user["favorites"] = []

            if movie_title in user["favorites"]:

                user["favorites"].remove(movie_title)

            break

    save_users(data)

    return redirect(url_for("favorites_page"))


# ---------------- ADD WATCH LATER ----------------

@app.route("/watch-later", methods=["POST"], endpoint="add_watch_later")
def add_watch_later():
    if "user" not in session:
        return redirect(url_for("login"))

    movie = request.form.get("movie", "").strip()

    if not movie:
        return redirect(url_for("home"))

    username = session["user"]
    data = load_users()

    for user in data.get("users", []):
        if user.get("username") == username:
            watch_later = user.setdefault("watch_later", [])

            if movie not in watch_later:
                watch_later.append(movie)

            save_users(data)
            return redirect(url_for("watch_later_page"))

    session.pop("user", None)
    return redirect(url_for("login"))


# ---------------- REMOVE WATCH LATER ----------------

@app.route("/remove_watchlater/<path:movie_title>", methods=["POST"])
def remove_watch_later(movie_title):

    if "user" not in session:

        return redirect(url_for("login"))

    username = session["user"]

    data = load_users()

    for user in data["users"]:

        if user["username"] == username:

            if "watch_later" not in user:

                user["watch_later"] = []

            if movie_title in user["watch_later"]:

                user["watch_later"].remove(movie_title)

            break

    save_users(data)

    return redirect(url_for("watch_later_page"))


# ---------------- WATCH LATER PAGE ----------------

@app.route("/watch-later")
def watch_later_page():

    if "user" not in session:

        return redirect(url_for("login"))

    username = session["user"]

    data = load_users()

    watch_later = []

    for user in data["users"]:

        if user["username"] == username:

            watch_later = user.get(
                "watch_later",
                []
            )

            break

    return render_template(
        "watchlater.html",
        watch_later=build_movie_cards(watch_later)
    )


# ==================================================
#                 NEW FEATURES
# ==================================================


# ---------------- RATE MOVIE ----------------

@app.route("/rate", methods=["POST"])
def rate_movie():

    if "user" not in session:

        return redirect(url_for("login"))

    movie = request.form["movie"]

    rating = request.form["rating"]

    username = session["user"]

    data = load_users()

    for user in data["users"]:

        if user["username"] == username:

            if "ratings" not in user:

                user["ratings"] = {}

            user["ratings"][movie] = int(rating)

            break

    save_users(data)

    return redirect(url_for("home"))


# ---------------- MARK MOVIE AS WATCHED ----------------

@app.route("/watched", methods=["POST"])
def mark_watched():

    if "user" not in session:

        return redirect(url_for("login"))

    movie = request.form["movie"]

    username = session["user"]

    data = load_users()

    for user in data["users"]:

        if user["username"] == username:

            if "watched" not in user:

                user["watched"] = []

            if movie not in user["watched"]:

                user["watched"].append(movie)

            break

    save_users(data)

    return redirect(url_for("home"))


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:

        return redirect(url_for("login"))

    username = session["user"]

    data = load_users()

    user_data = None

    for user in data["users"]:

        if user["username"] == username:

            user_data = user

            break

    if user_data is None:

        return redirect(url_for("login"))

    favorites = user_data.get(
        "favorites",
        []
    )

    watch_later = user_data.get(
        "watch_later",
        []
    )

    watched = user_data.get(
        "watched",
        []
    )

    ratings = user_data.get(
        "ratings",
        {}
    )

    # Generate personalized recommendations

    personalized_titles = personalized_recommend(
        favorites,
        watch_later,
        ratings,
        watched
    )

    # Get poster and movie details

    personalized_movies = build_movie_cards(
        personalized_titles
    )

    # Calculate average rating

    average_rating = 0

    if ratings:

        average_rating = round(
            sum(ratings.values()) / len(ratings),
            1
        )

    return render_template(
        "dashboard.html",
        username=username,
        favorites=favorites,
        watch_later=watch_later,
        watched=watched,
        ratings=ratings,
        personalized_movies=personalized_movies,
        total_favorites=len(favorites),
        total_watch_later=len(watch_later),
        total_watched=len(watched),
        total_ratings=len(ratings),
        average_rating=average_rating
    )


# ==================================================
#                 MOVIE FILTER
# ==================================================

@app.route("/filter", methods=["POST"], endpoint="filter_results")
def filter_results():
    genre = request.form.get("genre")
    min_year = request.form.get("min_year")
    max_year = request.form.get("max_year")

    filtered_titles = filter_movies(genre, min_year, max_year)
    filtered_movies = build_movie_cards(
        filtered_titles,
        use_external_details=False
    )

    return render_template(
        "index.html",
        filtered_movies=filtered_movies,
        filtered_count=len(filtered_movies)
    )


@app.route("/movie-details")
def movie_details():
    movie = request.args.get("title", "")

    if not movie:
        return jsonify({"poster": None})

    return jsonify(get_movie_details(movie))


# ---------------- USER PROFILE ----------------

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_users()
    user_data = None

    for u in data["users"]:
        if u["username"] == username:
            user_data = u
            break

    if user_data is None:
        session.pop("user", None)
        return redirect(url_for("login"))

    message = None
    message_type = "success"

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_email = request.form.get("email", "").strip()
        new_password = request.form.get("password", "").strip()

        if new_username and new_username != username:
            if any(u["username"] == new_username and u != user_data for u in data["users"]):
                message = "Username is already taken."
                message_type = "error"
            else:
                user_data["username"] = new_username
                session["user"] = new_username
                username = new_username

        if not message and new_email:
            user_data["email"] = new_email

        if not message and new_password:
            user_data["password"] = generate_password_hash(new_password)

        if not message:
            save_users(data)
            message = "Profile details updated successfully!"
            message_type = "success"

    favorites = user_data.get("favorites", [])
    watch_later = user_data.get("watch_later", [])
    watched = user_data.get("watched", [])
    ratings = user_data.get("ratings", {})

    return render_template(
        "profile.html",
        user=user_data,
        username=username,
        message=message,
        message_type=message_type,
        total_favorites=len(favorites),
        total_watch_later=len(watch_later),
        total_watched=len(watched),
        total_ratings=len(ratings)
    )


# ---------------- RUN APP ----------------

if __name__ == "__main__":

    app.run(debug=True)