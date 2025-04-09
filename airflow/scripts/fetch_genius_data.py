
import requests
import json
import os
import time
import datetime
from sqlalchemy import create_engine, text
import dotenv

# Load environment variables
dotenv.load_dotenv()

# AWS RDS & Genius API Configurations
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# Ensure API Token is loaded correctly
if not GENIUS_API_TOKEN:
    raise ValueError("ERROR: API Token not found! Check your .env file.")

# Debugging: Print part of the token
print(f"API Token Loaded: {GENIUS_API_TOKEN[:10]}... (length: {len(GENIUS_API_TOKEN)})")

# Genius API Headers
HEADERS = {"Authorization": f"Bearer {GENIUS_API_TOKEN.strip()}"}

# SQLAlchemy Engine (AWS RDS Connection)
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# List of 30 artists (One per day rotation)
ARTISTS = [
    "Taylor Swift", "Drake", "The Weeknd", "Beyoncé", "Kendrick Lamar",
    "Ed Sheeran", "Billie Eilish", "Adele", "Post Malone", "Harry Styles",
    "Bruno Mars", "Rihanna", "Justin Bieber", "Dua Lipa", "Travis Scott",
    "Ariana Grande", "J. Cole", "Doja Cat", "Shawn Mendes", "Lana Del Rey",
    "Lil Nas X", "Olivia Rodrigo", "Bad Bunny", "SZA", "Future",
    "Sam Smith", "The Chainsmokers", "Miley Cyrus", "Charlie Puth", "Jason Derulo"
]

def get_artist_for_today():
    """Returns the artist of the day (rotates daily)."""
    #today_index = datetime.datetime.today().timetuple().tm_yday % len(ARTISTS)
    hour_of_year = ( (datetime.datetime.now().timetuple().tm_yday - 1) * 24 + datetime.datetime.now().hour) % len(ARTISTS)
    return ARTISTS[hour_of_year]

def create_table_if_not_exists():
    """Ensure 'songs' table exists in AWS RDS."""
    with engine.connect() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS songs (
                id INT PRIMARY KEY,
                title TEXT NOT NULL,
                language TEXT,
                artist TEXT NOT NULL,
                album TEXT,
                description TEXT,
                release_date TEXT,
                pageviews INT,
                featured_artists TEXT,
                producer_artists TEXT,
                song_relationships JSONB,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ))
    print("Table 'songs' checked/created successfully.")

def extract_text_from_description(description_data):
    """Recursively extracts text from Genius description JSON."""
    text_parts = []
    
    def extract_text(obj):
        if isinstance(obj, str):  # If it's a string, add it
            text_parts.append(obj)
        elif isinstance(obj, dict) and "children" in obj:
            for child in obj["children"]:
                extract_text(child)
        elif isinstance(obj, list):
            for item in obj:
                extract_text(item)

    return " ".join(text_parts).strip() if text_parts else "No description available"

def get_song_details(song_id):
    """Fetch detailed song data from Genius API."""
    url = f"https://api.genius.com/songs/{song_id}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Error fetching song details (ID: {song_id}): {response.status_code}")
        return None
    
    song_data = response.json().get("response", {}).get("song", {})

    # Extract song description properly
    raw_description = song_data.get("description", {}).get("dom", {}).get("children", [])
    description = extract_text_from_description(raw_description)

    # Debug: Print extracted text to confirm
    # print(f"Extracted Description for {song_data.get('title')}: {description[:150]}...")

    return {
        "id": song_data.get("id"),
        "title": song_data.get("title"),
        "language": song_data.get("language", "Unknown"),  # Added language field
        "artist": song_data.get("primary_artist", {}).get("name"),
        "album": song_data.get("album", {}).get("name") if song_data.get("album") else None,
        "description": description,  # Extracted clean text
        "release_date": song_data.get("release_date", "Unknown"),
        "pageviews": song_data.get("stats", {}).get("pageviews"),
        "featured_artists": ", ".join([fa["name"] for fa in song_data.get("featured_artists", [])]),
        "producer_artists": ", ".join([pa["name"] for pa in song_data.get("producer_artists", [])]),
        "song_relationships": json.dumps([
            {"type": rel["type"], "songs": [s["title"] for s in rel.get("songs", [])]}
            for rel in song_data.get("song_relationships", [])
        ]),
        "url": song_data.get("url")
    }

def get_artist_songs(artist_name, max_songs=10):
    """Fetch songs from Genius API for a given artist."""
    url = f"https://api.genius.com/search?q={artist_name}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Error fetching data for {artist_name}: {response.status_code}")
        return []
    
    results = response.json().get("response", {}).get("hits", [])
    songs = []

    for hit in results[:max_songs]:  # Limit to max_songs per artist
        song_id = hit.get("result", {}).get("id")
        if song_id:
            song_info = get_song_details(song_id)  # Fetch full song details
            if song_info:
                songs.append(song_info)

    return songs

def insert_data_to_rds(songs):
    """Insert multiple song records into AWS RDS PostgreSQL, updating existing records if needed."""
    if songs:
        with engine.connect() as conn:
            for song in songs:
                conn.execute(text(
                    """
                    INSERT INTO songs (id, title, language, artist, album, description, release_date, pageviews, 
                                      featured_artists, producer_artists, song_relationships, url, created_at)
                    VALUES (:id, :title, :language, :artist, :album, :description, :release_date, :pageviews, 
                            :featured_artists, :producer_artists, :song_relationships, :url, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING;
                    """
                ), song)
                print(f"Inserted: {song['title']} by {song['artist']}")

# Run the script
if __name__ == "__main__":
    create_table_if_not_exists()  # Ensure table exists
    artist_of_the_day = get_artist_for_today()
    print(f"🎵 Fetching songs for: {artist_of_the_day}")

    songs = get_artist_songs(artist_of_the_day)
    insert_data_to_rds(songs)
