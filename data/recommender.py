import re
import requests
import pandas as pd
import difflib
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# LOAD DATASET
# ============================================================

movies = pd.read_csv("data/ml-latest-small/movies.csv")


# Handle missing genres
movies["genres"] = movies["genres"].fillna("")


# ============================================================
# TF-IDF CONTENT-BASED RECOMMENDER
# ============================================================

tfidf = TfidfVectorizer(stop_words="english")

tfidf_matrix = tfidf.fit_transform(movies["genres"])


# Calculate cosine similarity
similarity = cosine_similarity(tfidf_matrix)


# Create title-to-index mapping
indices = pd.Series(
    movies.index,
    index=movies["title"].str.casefold()
).drop_duplicates()


# ============================================================
# NORMAL MOVIE RECOMMENDATION
# ============================================================

def recommend(title):

    # Clean user input
    title = title.strip().casefold()

    # Convert titles to lowercase
    all_titles = movies["title"].str.casefold().tolist()


    # First try substring matching
    substring_matches = [
        movie
        for movie in all_titles
        if title in movie
    ]


    # If substring match found
    if substring_matches:

        matched_title = substring_matches[0]


    # Otherwise use fuzzy matching
    else:

        matches = difflib.get_close_matches(
            title,
            all_titles,
            n=1,
            cutoff=0.6
        )


        # No movie found
        if not matches:
            return None


        matched_title = matches[0]


    # Get movie index
    index = indices[matched_title]


    # Get similarity scores
    similarity_scores = list(
        enumerate(similarity[index])
    )


    # Sort by similarity
    similarity_scores = sorted(
        similarity_scores,
        key=lambda x: x[1],
        reverse=True
    )


    # Skip the movie itself
    similarity_scores = similarity_scores[1:6]


    # Get movie indexes
    movie_indices = [
        i[0]
        for i in similarity_scores
    ]


    # Get movie titles
    recommended_movies = movies[
        "title"
    ].iloc[movie_indices]


    return matched_title, recommended_movies.tolist()


# ============================================================
# PERSONALIZED RECOMMENDATIONS
# ============================================================

def personalized_recommend(
    favorites,
    watch_later,
    ratings,
    watched
):

    """
    Generate personalized movie recommendations based on:

    - Favorite movies
    - Watch Later movies
    - Movies rated 4 or 5 stars
    - Watched movies to exclude
    """


    # Combine movies showing user interest
    liked_movies = []


    # Favorites are strong preferences
    liked_movies.extend(favorites)


    # Watch Later shows interest
    liked_movies.extend(watch_later)


    # Add highly rated movies
    for movie, rating in ratings.items():

        if int(rating) >= 4:
            liked_movies.append(movie)


    # Remove duplicates
    liked_movies = list(
        dict.fromkeys(liked_movies)
    )


    # No preferences yet
    if not liked_movies:
        return []


    recommended_scores = {}


    # Generate recommendations
    # from each liked movie
    for movie in liked_movies:

        movie_key = movie.strip().casefold()


        # Movie doesn't exist in dataset
        if movie_key not in indices:
            continue


        index = indices[movie_key]


        # Similarity scores
        similarity_scores = list(
            enumerate(similarity[index])
        )


        # Sort by similarity
        similarity_scores = sorted(
            similarity_scores,
            key=lambda x: x[1],
            reverse=True
        )


        # Take top 10 similar movies
        for movie_index, score in similarity_scores[1:11]:

            recommended_movie = movies[
                "title"
            ].iloc[movie_index]


            # Don't recommend watched movies
            if recommended_movie in watched:
                continue


            # Don't recommend favorites again
            if recommended_movie in favorites:
                continue


            # Add score
            if recommended_movie not in recommended_scores:

                recommended_scores[
                    recommended_movie
                ] = 0


            recommended_scores[
                recommended_movie
            ] += score


    # Sort recommendations
    sorted_recommendations = sorted(
        recommended_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )


    # Return top 5
    return [
        movie
        for movie, score in sorted_recommendations[:5]
    ]


# ============================================================
# FILTER MOVIES
# ============================================================

def filter_movies(
    genre=None,
    min_year=None,
    max_year=None,
    min_rating=None
):

    """
    Filter movies based on:

    - Genre
    - Minimum year
    - Maximum year
    - Minimum IMDb rating

    Note:
    MovieLens contains genre and year information.
    IMDb rating filtering will be handled using OMDb data.
    """


    # Make a copy of the dataset
    filtered_movies = movies.copy()


    # --------------------------------------------------------
    # FILTER BY GENRE
    # --------------------------------------------------------

    if genre and genre != "All":

        filtered_movies = filtered_movies[
            filtered_movies["genres"].str.contains(
                genre,
                case=False,
                na=False
            )
        ]


    # --------------------------------------------------------
    # EXTRACT YEAR FROM TITLE
    # --------------------------------------------------------

    filtered_movies["year"] = (
        filtered_movies["title"]
        .str.extract(r"\((\d{4})\)")
        .astype(float)
    )


    # --------------------------------------------------------
    # FILTER BY MINIMUM YEAR
    # --------------------------------------------------------

    if min_year:

        filtered_movies = filtered_movies[
            filtered_movies["year"] >= int(min_year)
        ]


    # --------------------------------------------------------
    # FILTER BY MAXIMUM YEAR
    # --------------------------------------------------------

    if max_year:

        filtered_movies = filtered_movies[
            filtered_movies["year"] <= int(max_year)
        ]


    # Return movie titles
    return filtered_movies[
        "title"
    ].tolist()


# ============================================================
# OMDb MOVIE DETAILS
# ============================================================

def get_local_movie_details(movie_name):
    movie = movies[movies["title"] == movie_name]

    if movie.empty:
        return {
            "poster": None,
            "rating": "N/A",
            "genre": "N/A",
            "year": "N/A"
        }

    title = movie.iloc[0]["title"]
    year_match = re.search(r"\((\d{4})\)", title)

    return {
        "poster": None,
        "rating": "N/A",
        "genre": movie.iloc[0]["genres"].replace("|", ", "),
        "year": year_match.group(1) if year_match else "N/A"
    }


@lru_cache(maxsize=512)
def get_movie_details(movie_name):

    api_key = os.environ.get("OMDB_API_KEY")


    # Remove year from movie title
    clean_title = re.sub(
        r"\(\d{4}\)",
        "",
        movie_name
    ).strip()


    # OMDb API URL
    url = (
        f"https://www.omdbapi.com/"
        f"?t={clean_title}"
        f"&apikey={api_key}"
    )


    try:

        response = requests.get(
            url,
            timeout=10
        )

        data = response.json()


    except Exception:

        return {
    "poster": None,
    "rating": "N/A",
    "genre": "N/A",
    "year": "N/A",
    "plot": "N/A"
}


    # Movie found
    if data.get("Response") == "True":

        poster = data.get("Poster")


        if poster == "N/A":
            poster = None


        return {
    "poster": poster,
    "rating": data.get("imdbRating", "N/A"),
    "genre": data.get("Genre", "N/A"),
    "year": data.get("Year", "N/A"),
    "plot": data.get("Plot", "N/A")
}


    # Movie not found
    return {
    "poster": None,
    "rating": "N/A",
    "genre": "N/A",
    "year": "N/A",
    "plot": "N/A"
}


# ============================================================
# GET ALL MOVIE TITLES
# ============================================================

def get_all_titles():

    return movies[
        "title"
    ].tolist()