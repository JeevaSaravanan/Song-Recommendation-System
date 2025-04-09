from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
import time

# Default DAG arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 3, 22),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'train_knn_model',
    default_args=default_args,
    description='Train KNN model and log results in MLflow',
    schedule_interval=None,  
    catchup=False,
)

# Define the task to run the training script
train_knn_task = BashOperator(
    task_id='train_knn',
    bash_command='python /opt/airflow/scripts/train_knn.py > /tmp/train_knn_out.log 2>&1',
    dag=dag,
)

# Add this at the end of your DAG definition
trigger_restart_api = TriggerDagRunOperator(
    task_id="trigger_restart_api",
    trigger_dag_id="restart_fastapi_after_knn",
)

def wait_a_bit():
    time.sleep(20)  # Delay to allow MLflow to finish registering artifacts

wait_task = PythonOperator(
    task_id="wait_for_register",
    python_callable=wait_a_bit,
    execution_timeout=timedelta(minutes=15),
    dag=dag
)

train_knn_task >> wait_task >> trigger_restart_api
