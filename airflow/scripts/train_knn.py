import os
import pandas as pd
import mlflow
import mlflow.sklearn
from mlflow import MlflowClient
from sqlalchemy import create_engine
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import dotenv
import pickle

# Load environment variables
dotenv.load_dotenv()

# Database credentials
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# MLflow Tracking Server
MLFLOW_TRACKING_URI = "http://localhost:5001"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("knn-recommender")  # 👈 Creates it if doesn't exist

# MLflow config
client = MlflowClient()
MODEL_NAME = "knn-cosine-recommender"

# Database connection
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def fetch_data():
    """Fetch pageviews and artist from AWS RDS."""
    query = "SELECT id, pageviews, artist FROM songs WHERE pageviews IS NOT NULL AND artist IS NOT NULL"
    df = pd.read_sql(query, engine)
    return df

def train_knn_model(n_neighbors=5):
    df = fetch_data()
    features = df[['pageviews', 'artist']]
    song_ids = df['id'].tolist()

    # Preprocessing pipeline
    preprocessor = ColumnTransformer([
        ('num', StandardScaler(), ['pageviews']),
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['artist']),
    ])

    # Transform features first
    X_transformed = preprocessor.fit_transform(features)

    # Train KNN directly on transformed features
    knn = NearestNeighbors(n_neighbors=n_neighbors, metric='cosine')
    knn.fit(X_transformed)

    # Wrap everything in a Pipeline for logging
    model = Pipeline([
        ('preprocessor', preprocessor),
        ('knn', knn),
    ])

    return model, X_transformed, song_ids

def log_model(model, X_transformed, song_ids, n_neighbors):
    with mlflow.start_run():
        mlflow.log_param("n_neighbors", n_neighbors)

        # Save transformed matrix and song IDs
        os.makedirs("metadata", exist_ok=True)
        metadata_path = "metadata/song_metadata.pkl"
        with open(metadata_path, "wb") as f:
            pickle.dump({
                "song_ids": song_ids,
                "X_transformed": X_transformed,
            }, f)
        mlflow.log_artifact(metadata_path, artifact_path="metadata")
        os.remove(metadata_path)

        # Log the model
        mlflow.sklearn.log_model(model, "knn_cosine_model")
        print("KNN model and artifacts logged in MLflow.")

        # Register model
        if MODEL_NAME not in [m.name for m in client.search_registered_models()]:
            client.create_registered_model(MODEL_NAME)

        run_id = mlflow.active_run().info.run_id
        model_uri = f"runs:/{run_id}/knn_cosine_model"
        version = client.create_model_version(MODEL_NAME, model_uri, run_id)
        client.set_registered_model_alias(MODEL_NAME, "champion", version.version)
        print(f"Registered as '{MODEL_NAME}' version {version.version} and set as @champion.")

if __name__ == "__main__":
    knn_model, X_transformed, song_ids = train_knn_model(n_neighbors=5)
    log_model(knn_model, X_transformed, song_ids, n_neighbors=5)
