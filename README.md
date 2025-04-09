# Song Recommendation System

This project is an end-to-end pipeline that fetches song data from the Genius API, stores it in an AWS RDS PostgreSQL database, trains a KNN model to create song recommendations, and serves the recommendations via a FastAPI endpoint. The pipeline orchestration is handled by Apache Airflow, while MLflow is used for experiment tracking and model management.

## Table of Contents

- - [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup and Configuration](#setup-and-configuration)
- [Running the Application](#running-the-application)
- [Usage](#usage)

## Architecture 
![](/assets/images/architecture.png)


## Features

- **Data Fetching:** Periodically fetches song data for a rotating list of artists using the Genius API.
- **Database Integration:** Stores fetched song details in an AWS RDS PostgreSQL database.
- **Model Training:** Trains a KNN model on song data (using pageviews and artist information) to recommend similar songs.
- **MLflow Integration:** Logs training artifacts, registers the KNN model, and promotes the best model as the current champion.
- **API Service:** Serves song recommendations via a FastAPI service.
- **Airflow Orchestration:** Uses Apache Airflow to schedule and trigger tasks, including:
  - Fetching data (`fetch_genius_songs` DAG)
  - Training the KNN model (`train_knn_model` DAG)
  - Restarting the FastAPI service after training (`restart_fastapi_after_knn` DAG)

## Project Structure

```plaintext
.
├── airflow
│   ├── dags
│   │   ├── genius_dag.py              # Fetches Genius data and triggers KNN training
│   │   ├── restart_fastapi_dag.py       # Restarts FastAPI after KNN model is trained
│   │   └── train_knn_dag.py             # Trains the KNN model and logs results in MLflow
│   ├── scripts
│   │   ├── fetch_genius_data.py         # Script to fetch song data from Genius API and insert into RDS
│   │   └── train_knn.py                 # Script to train the KNN model and log with MLflow
│   └── Dockerfile                       # Dockerfile for Airflow image with dependencies
├── fastapi
│   ├── app.py                           # FastAPI application serving recommendations
│   └── Dockerfile                       # Dockerfile for FastAPI service
└── docker-compose.yaml                  # Compose file to orchestrate Airflow, FastAPI, Postgres, and Redis
```

## Prerequisites

- Docker
- Docker Compose
- Valid AWS RDS credentials for PostgreSQL
- A valid Genius API token
- (Optional) MLflow Tracking server (configured via Docker in this setup)

## Setup and Configuration

1. **Environment Variables:**

   Create a `.env` file in the root directory (or set these variables in your deployment environment) with the following keys:

   ```dotenv
   GENIUS_API_TOKEN=your_genius_api_token
   DB_USER=your_db_username
   DB_PASS=your_db_password
   DB_HOST=your_db_host
   DB_PORT=5432
   DB_NAME=your_db_name
   ```

2. **Docker Setup:**

   The project uses Docker Compose to orchestrate the services. The `docker-compose.yaml` file defines services for:
   
   - **Postgres:** For storing Airflow metadata and song data.
   - **Redis:** For Celery broker.
   - **Airflow:** Webserver, Scheduler, Worker, Triggerer, and an Init service.
   - **FastAPI:** The recommendation service.
   
3. **Airflow Configuration:**

   - DAGs are located in `airflow/dags`.
   - Scripts are located in `airflow/scripts`.
   - Airflow is configured to run with the Celery Executor.

## Running the Application

1. **Start Services:**

   In your project root, run:

   ```bash
   docker-compose up --build
   ```

   This will build the images and start all services defined in the `docker-compose.yaml`.

2. **Accessing the Services:**

   - **Airflow Web UI:** [http://localhost:8080](http://localhost:8080)
   - **MLflow UI:** [http://localhost:5001](http://localhost:5001) (accessible via the Airflow worker)
   - **FastAPI Service:** [http://localhost:8000](http://localhost:8000)

3. **Triggering the Pipeline:**

   - The `fetch_genius_songs` DAG in Airflow automatically runs every hour.
   - The KNN training DAG (`train_knn_model`) is triggered after fetching completes.
   - After training, the FastAPI service is restarted to load the new model.

## Usage

- **Fetching Data and Training:**
  - The Airflow DAG `fetch_genius_songs` runs a Bash script to execute `fetch_genius_data.py`.
  - Once the data is fetched and stored, the DAG triggers `train_knn_model` to train the model.
  
- **Making Recommendations:**
  - Use the FastAPI endpoint to get song recommendations:
  
    ```bash
    curl "http://localhost:8000/recommend/0?k=5"
    ```
  
  - The endpoint takes:
    - `index`: Index of the song from which to recommend similar songs.
    - `k`: Number of recommendations.