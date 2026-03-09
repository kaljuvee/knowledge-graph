import requests
import time
from utils.config import TMDB_API_KEY, TMDB_BASE_URL, OMDB_API_KEY


def get_popular_movies(pages=5):
    """Fetch popular movies from TMDB. 20 movies per page."""
    movies = []
    for page in range(1, pages + 1):
        resp = requests.get(
            f"{TMDB_BASE_URL}/movie/popular",
            params={"api_key": TMDB_API_KEY, "page": page},
        )
        resp.raise_for_status()
        movies.extend(resp.json().get("results", []))
        time.sleep(0.25)
    return movies


def get_movie_details(movie_id):
    """Fetch full movie details including credits and keywords."""
    resp = requests.get(
        f"{TMDB_BASE_URL}/movie/{movie_id}",
        params={
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits,keywords",
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_omdb_data(imdb_id):
    """Enrich with OMDB data (ratings, awards)."""
    if not OMDB_API_KEY or not imdb_id:
        return None
    resp = requests.get(
        "http://www.omdbapi.com/",
        params={"apikey": OMDB_API_KEY, "i": imdb_id},
    )
    data = resp.json()
    if data.get("Response") == "True":
        return data
    return None


def build_graph_data(popular_movies, progress_callback=None):
    """
    Fetch details for each movie and build a structured dataset
    suitable for loading into Neo4j and ChromaDB.
    """
    all_movies = []
    all_people = {}
    all_genres = {}
    all_companies = {}
    all_keywords = {}

    for i, movie in enumerate(popular_movies):
        if progress_callback:
            progress_callback(i, len(popular_movies), movie.get("title", ""))

        details = get_movie_details(movie["id"])
        time.sleep(0.25)

        movie_data = {
            "tmdb_id": details["id"],
            "imdb_id": details.get("imdb_id"),
            "title": details["title"],
            "overview": details.get("overview", ""),
            "tagline": details.get("tagline", ""),
            "release_date": details.get("release_date", ""),
            "vote_average": details.get("vote_average", 0),
            "vote_count": details.get("vote_count", 0),
            "popularity": details.get("popularity", 0),
            "budget": details.get("budget", 0),
            "revenue": details.get("revenue", 0),
            "runtime": details.get("runtime", 0),
            "original_language": details.get("original_language", ""),
            "genres": [],
            "production_companies": [],
            "keywords": [],
            "cast": [],
            "directors": [],
        }

        # Genres
        for g in details.get("genres", []):
            all_genres[g["id"]] = {"tmdb_id": g["id"], "name": g["name"]}
            movie_data["genres"].append(g["id"])

        # Production companies
        for c in details.get("production_companies", []):
            all_companies[c["id"]] = {
                "tmdb_id": c["id"],
                "name": c["name"],
                "origin_country": c.get("origin_country", ""),
            }
            movie_data["production_companies"].append(c["id"])

        # Keywords
        for k in details.get("keywords", {}).get("keywords", []):
            all_keywords[k["id"]] = {"tmdb_id": k["id"], "name": k["name"]}
            movie_data["keywords"].append(k["id"])

        # Cast (top 10)
        credits = details.get("credits", {})
        for actor in credits.get("cast", [])[:10]:
            pid = actor["id"]
            movie_data["cast"].append(
                {
                    "person_id": pid,
                    "character": actor.get("character", ""),
                    "credit_order": actor.get("order", 0),
                }
            )
            if pid not in all_people:
                all_people[pid] = {
                    "tmdb_id": pid,
                    "name": actor["name"],
                    "popularity": actor.get("popularity", 0),
                    "known_for_department": actor.get(
                        "known_for_department", "Acting"
                    ),
                }

        # Directors
        for crew in credits.get("crew", []):
            if crew["job"] == "Director":
                pid = crew["id"]
                movie_data["directors"].append(pid)
                if pid not in all_people:
                    all_people[pid] = {
                        "tmdb_id": pid,
                        "name": crew["name"],
                        "popularity": crew.get("popularity", 0),
                        "known_for_department": "Directing",
                    }

        # OMDB enrichment
        if OMDB_API_KEY and details.get("imdb_id"):
            omdb = get_omdb_data(details["imdb_id"])
            if omdb:
                movie_data["imdb_rating"] = omdb.get("imdbRating", "N/A")
                movie_data["metascore"] = omdb.get("Metascore", "N/A")
                movie_data["awards"] = omdb.get("Awards", "")
            time.sleep(0.25)

        all_movies.append(movie_data)

    return {
        "movies": all_movies,
        "people": list(all_people.values()),
        "genres": list(all_genres.values()),
        "production_companies": list(all_companies.values()),
        "keywords": list(all_keywords.values()),
    }
