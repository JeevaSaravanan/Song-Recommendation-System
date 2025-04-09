from fastapi import FastAPI
import mlflow.sklearn
from mlflow import MlflowClient
import pandas as pd
import os

app = FastAPI()

MODEL_NAME = "knn-cosine-recommender"
MODEL_VERSION_FILE = "/fastapi/logs/last_model_version.txt"  # Persisted across reboots
MODEL_METADATA_PATH = "metadata/song_metadata.pkl"

model = None
song_ids = None
X_transformed = None  # Feature matrix for neighbor lookup

mlflow.set_tracking_uri("http://airflow-worker:5001")
client = MlflowClient()

def get_last_loaded_version():
    """Read last loaded model version from file."""
    if os.path.exists(MODEL_VERSION_FILE):
        with open(MODEL_VERSION_FILE, "r") as f:
            return f.read().strip()
    else:
        with open(MODEL_VERSION_FILE, "w") as f:
            f.write("")
            return None

def save_last_loaded_version(version):
    """Save current model version to file."""
    with open(MODEL_VERSION_FILE, "w") as f:
        f.write(str(version))

def load_model_and_data(force_reload=False):
    global model, song_ids, X_transformed

    # Get current @champion version from MLflow
    champion_info = client.get_model_version_by_alias(MODEL_NAME, "champion")
    current_version = champion_info.version
    last_version = get_last_loaded_version()

    if force_reload or current_version != last_version:
        print(f"Loading new model version {current_version}...", flush=True)
        model_uri = f"models:/{MODEL_NAME}@champion"
        model = mlflow.sklearn.load_model(model_uri)

        # Load associated song_ids and precomputed features
        run_id = champion_info.run_id
        local_path = client.download_artifacts(run_id, MODEL_METADATA_PATH)
        metadata = pd.read_pickle(local_path)
        song_ids = metadata["song_ids"]
        X_transformed = metadata["X_transformed"]

        save_last_loaded_version(current_version)
        print("Model, song_ids, and feature matrix loaded.", flush=True)
    else:
        print("Model already up-to-date.", flush=True)

@app.on_event("startup")
def startup_event():
    load_model_and_data(force_reload=True)  # Load at startup

@app.get("/recommend/{index}")
def recommend(index: int, k: int = 5):
    if model is None or song_ids is None or X_transformed is None:
        return {"error": "Model not loaded."}

    if index >= X_transformed.shape[0]:
        return {"error": f"Index out of range. Dataset has {X_transformed.shape[0]} songs."}

    # Use only the knn step from the pipeline
    knn_model = model.named_steps['knn']
    distances, indices = knn_model.kneighbors(X_transformed[index], n_neighbors=k + 1)

    recommended_ids = [song_ids[i] for i in indices.flatten() if i != index][:k]

    return {
        "requested_song_id": song_ids[index],
        "recommended_song_ids": recommended_ids
    }
