from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime, timedelta

# Default DAG arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 3, 22),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'fetch_genius_songs',
    default_args=default_args,
    description='Fetch song data from Genius API and store in AWS RDS',
    schedule_interval='@hourly',  # Runs every hour
    catchup=False,
)

# Task to fetch and store data
run_script = BashOperator(
    task_id='run_fetch_script',
    bash_command='python /opt/airflow/scripts/fetch_genius_data.py',
    dag=dag,
)

# Trigger train_knn_model DAG after fetching is done
trigger_training = TriggerDagRunOperator(
    task_id='trigger_train_knn',
    trigger_dag_id='train_knn_model',
    wait_for_completion=False,  # Set to True if you want to wait for completion before next fetch
    dag=dag,
)

# Define task order
run_script >> trigger_training
