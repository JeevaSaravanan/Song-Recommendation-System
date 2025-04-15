import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import requests
from dotenv import load_dotenv

# Set page configuration
st.set_page_config(
    page_title="Music Explorer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to make it look like Spotify
st.markdown("""
<style>
    /* Overall styling */
    .main {
        background-color: #121212;
        color: white;
    }
    .stApp {
        background-color: #121212;
    }
    h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }
    .stSidebar {
        background-color: #000000;
    }
    /* Cards styling */
    .song-card {
        background-color: #181818;
        border-radius: 8px;
        padding: 16px;
        transition: background-color 0.3s;
        cursor: pointer;
    }
    .song-card:hover {
        background-color: #282828;
    }
    .song-title {
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 4px;
        color: white;
    }
    .song-artist {
        color: #b3b3b3;
        font-size: 14px;
    }
    .song-views {
        color: #b3b3b3;
        font-size: 12px;
        margin-top: 8px;
    }
    /* Button styling */
    .stButton>button {
        background-color: #1DB954;
        color: white;
        border-radius: 30px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1ed760;
    }
    /* Progress bar */
    .stProgress > div > div {
        background-color: #1DB954;
    }
    /* Recommendations section */
    .recommendations-section {
        background-color: #282828;
        border-radius: 8px;
        padding: 16px;
        margin-top: 20px;
    }
    .recommendation-title {
        font-weight: bold;
        color: white;
        margin-bottom: 10px;
    }
    .recommendation-item {
        display: flex;
        align-items: center;
        padding: 8px;
        border-radius: 4px;
        transition: background-color 0.3s;
    }
    .recommendation-item:hover {
        background-color: #383838;
    }
</style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# Database credentials
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# FastAPI endpoint for recommendations
RECOMMENDATION_API_URL = os.getenv("RECOMMENDATION_API_URL", "http://localhost:8000")

# Function to fetch data
@st.cache_data(ttl=300)
def fetch_data():
    """Fetch songs data from PostgreSQL."""
    try:
        # Create engine
        connection_string = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(connection_string)
        
        # Create connection and execute query
        with engine.connect() as connection:
            query = text("""
            SELECT id, pageviews, artist, title 
            FROM songs 
            WHERE pageviews IS NOT NULL AND artist IS NOT NULL
            ORDER BY pageviews DESC
            LIMIT 10000
            """)
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        # Return sample data if database connection fails
        return pd.DataFrame({
            'id': range(1, 11),
            'pageviews': [1254890, 987654, 876543, 765432, 654321, 543210, 432109, 321098, 210987, 109876],
            'artist': ['The Weeknd', 'Ed Sheeran', 'Billie Eilish', 'Drake', 'Taylor Swift', 'Dua Lipa', 'Post Malone', 'Ariana Grande', 'BTS', 'Justin Bieber'],
            'title': ['Blinding Lights', 'Shape of You', 'Bad Guy', 'God\'s Plan', 'Anti-Hero', 'Don\'t Start Now', 'Circles', 'Positions', 'Dynamite', 'Stay']
        })

# Function to get song recommendations
def get_recommendations(song_index, num_recommendations=5):
    """Get song recommendations from FastAPI."""
    try:
        response = requests.get(f"{RECOMMENDATION_API_URL}/recommend/{song_index}?k={num_recommendations}")
        if response.status_code == 200:
            return response.json()
        else:
            st.warning(f"Failed to get recommendations: {response.text}")
            return None
    except Exception as e:
        st.warning(f"Error getting recommendations: {str(e)}")
        return None

# Function to get song details by ID
def get_song_by_id(song_id, df):
    """Find song in dataframe by ID."""
    song = df[df['id'] == song_id]
    if not song.empty:
        return song.iloc[0]
    return None

# Function to get cover image
@st.cache_data(ttl=6000)
def get_cover_image(song, artist):
    try:
        query = f"{song} {artist}"
        url = f"https://itunes.apple.com/search?term={requests.utils.quote(query)}&limit=1"
        res = requests.get(url).json()
        if res['resultCount']:
            return res['results'][0]['artworkUrl100'].replace('100x100', '600x600')
    except Exception:
        pass
    return None

# Function to format large numbers
def format_number(num):
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

# Initialize session state for selected song
if 'selected_song' not in st.session_state:
    st.session_state.selected_song = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

# Main content
st.title("🎵 Music Explorer")

# Fetch data
df = fetch_data()

# Create a mapping of song IDs to dataframe indices
id_to_index = {}
for i, row in df.iterrows():
    id_to_index[row['id']] = i

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Spotify_icon.svg/1982px-Spotify_icon.svg.png", width=50)
    st.title("Music Explorer")
    
    st.subheader("Filters")
    
    # Get unique artists for filter
    artists = ['All Artists'] + sorted(df['artist'].unique().tolist())
    selected_artist = st.selectbox("Artist", artists)
    
    # Views filter
    min_views = int(df['pageviews'].min())
    max_views = int(df['pageviews'].max())
    views_range = st.slider("Minimum Views", min_views, max_views, min_views)
    
    # Sort options
    sort_options = ["Most Popular", "Least Popular", "Artist (A-Z)", "Title (A-Z)"]
    sort_by = st.selectbox("Sort by", sort_options)
    
    # Search box
    search_query = st.text_input("Search songs or artists")
    
    # Number of recommendations
    num_recommendations = st.slider("Number of Recommendations", 1, 10, 5)

# User greeting and statistics
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 20px;">
    <div style="background-color: #1DB954; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; margin-right: 10px;">
        <span style="color: white; font-weight: bold;">👤</span>
    </div>
    <div>
        <div style="font-weight: bold; font-size: 18px;">Welcome back!</div>
        <div style="color: #b3b3b3; font-size: 14px;">Explore your music stats</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Apply filters
filtered_df = df.copy()

# Filter by artist
if selected_artist != "All Artists":
    filtered_df = filtered_df[filtered_df['artist'] == selected_artist]

# Filter by views
filtered_df = filtered_df[filtered_df['pageviews'] >= views_range]

# Apply search filter
if search_query:
    filtered_df = filtered_df[
        filtered_df['title'].str.contains(search_query, case=False) | 
        filtered_df['artist'].str.contains(search_query, case=False)
    ]

# Apply sorting
if sort_by == "Most Popular":
    filtered_df = filtered_df.sort_values(by='pageviews', ascending=False)
elif sort_by == "Least Popular":
    filtered_df = filtered_df.sort_values(by='pageviews', ascending=True)
elif sort_by == "Artist (A-Z)":
    filtered_df = filtered_df.sort_values(by='artist')
elif sort_by == "Title (A-Z)":
    filtered_df = filtered_df.sort_values(by='title')

# Display the number of results
st.write(f"Found {len(filtered_df)} songs")

# Function to handle song click
def handle_song_click(song_id):
    index = id_to_index.get(song_id, 0)
    st.session_state.selected_song = song_id
    # Get recommendations
    recommendations = get_recommendations(index, num_recommendations)
    if recommendations:
        st.session_state.recommendations = recommendations
def handle_like_click(song_id):
    song = get_song_by_id(song_id, df)
    if song is not None:
        st.success(f"Liked")

if not filtered_df.empty:
    # Use columns for responsive layout
    for i in range(0, len(filtered_df), 3):
        cols = st.columns(3)
        for j in range(3):
            if i+j < len(filtered_df):
                song = filtered_df.iloc[i+j]
                with cols[j]:
                    cover_img = get_cover_image(song['title'], song['artist'])
                    
                    # Create a clickable card
                    card_html = f"""
                    <div class="song-card" onclick="handleSongClick({song['id']})">
                        <div style="text-align: center; margin-bottom: 10px;">
                            <img src="{cover_img if cover_img else '/api/placeholder/300/300'}" style="width: 100%; border-radius: 4px;" alt="{song['title']}">
                        </div>
                        <div class="song-title">{song['title']}</div>
                        <div class="song-artist">{song['artist']}</div>
                        <div class="song-views">🎧 {format_number(song['pageviews'])} plays</div>
                    </div>
                    """
                    
                    st.markdown(card_html, unsafe_allow_html=True)
                
                    if st.button(f"▶ Play ", key=f"song_{song['id']}"):
                        handle_song_click(song['id'])
                    
else:
    st.info("No songs found matching your criteria. Try adjusting your filters.")

# Display recommendations if a song is selected
if st.session_state.selected_song and st.session_state.recommendations:
    st.markdown("---")
    
    # Get selected song details
    selected_song = get_song_by_id(st.session_state.selected_song, df)
    if selected_song is not None:
        # Display selected song
        st.subheader("Now Playing")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            cover_img = get_cover_image(selected_song['title'], selected_song['artist'])
            st.image(cover_img if cover_img else "/api/placeholder/300/300", width=200)
        
        with col2:
            st.markdown(f"### {selected_song['title']}")
            st.markdown(f"#### {selected_song['artist']}")
            st.markdown(f"👁️ {format_number(selected_song['pageviews'])} views")
    
    # Display recommendations
    st.subheader("Recommended Songs")
    recommendations = st.session_state.recommendations
    
    # Create columns for recommendations
    cols = st.columns(5)
    print(recommendations)
    
    for i, song_id in enumerate(recommendations.get('recommended_song_ids', [])):
        
        recommended_song = get_song_by_id(song_id, df)
        print("song_id",song_id,recommended_song['title'],recommended_song['artist'])
        if recommended_song is not None:
            with cols[i % 5]:
                cover_img = get_cover_image(recommended_song['title'], recommended_song['artist'])
                st.image(cover_img if cover_img else "https://creativemeadow.com/wp-content/uploads/2023/02/3766_cat_on_toilet_funny_9586-150x150.jpeg", width=150)
                st.markdown(f"**{recommended_song['title']}**")
                st.markdown(f"{recommended_song['artist']}")
                
                sub_cols= st.columns(2)
                with sub_cols[0]:   
                    if st.button(f"Play", key=f"rec_{song_id}"):
                        handle_song_click(song_id)

                with sub_cols[1]:
                    if (st.button("♡", key=f"rec_like_{song_id}")):
                        handle_like_click(song_id)

# Now playing section (fixed at the bottom)
if st.session_state.selected_song:
    selected_song = get_song_by_id(st.session_state.selected_song, df)
    if selected_song is not None:
        cover_img = get_cover_image(selected_song['title'], selected_song['artist'])
        now_playing_html = f"""
        <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: #181818; padding: 10px; z-index: 1000; border-top: 1px solid #282828; display: flex; align-items: center;">
            <div style="width: 60px; height: 60px; margin-right: 15px;">
                <img src="{cover_img if cover_img else '/api/placeholder/60/60'}" style="width: 100%; border-radius: 4px;" alt="Now playing">
            </div>
            <div style="flex-grow: 1;">
                <div style="font-weight: bold; color: white;">{selected_song['title']}</div>
                <div style="color: #b3b3b3; font-size: 14px;">{selected_song['artist']}</div>
            </div>
            <div style="margin-right: 20px; display: flex; align-items: center;">
                <div style="color: white; font-size: 24px; cursor: pointer; margin-right: 15px;">⏮</div>
                <div style="color: white; font-size: 32px; cursor: pointer; margin-right: 15px;">▶</div>
                <div style="color: white; font-size: 24px; cursor: pointer;">⏭</div>
            </div>
        </div>
        """
        st.markdown(now_playing_html, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: #181818; padding: 10px; z-index: 1000; border-top: 1px solid #282828; display: flex; align-items: center;">
        <div style="width: 60px; height: 60px; margin-right: 15px;">
            <img src="/api/placeholder/60/60" style="width: 100%; border-radius: 4px;" alt="Now playing">
        </div>
        <div style="flex-grow: 1;">
            <div style="font-weight: bold; color: white;">Select a song to play</div>
            <div style="color: #b3b3b3; font-size: 14px;">Artist name will appear here</div>
        </div>
        <div style="margin-right: 20px; display: flex; align-items: center;">
            <div style="color: white; font-size: 24px; cursor: pointer; margin-right: 15px;">⏮</div>
            <div style="color: white; font-size: 32px; cursor: pointer; margin-right: 15px;">▶</div>
            <div style="color: white; font-size: 24px; cursor: pointer;">⏭</div>
        </div>
    </div>
    """, unsafe_allow_html=True)