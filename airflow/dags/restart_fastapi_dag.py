from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="restart_fastapi_after_knn",
    default_args=default_args,
    description="Restart FastAPI service after KNN training",
    schedule_interval=None,  # only triggered from another DAG
    catchup=False
)

restart_fastapi = BashOperator(
        task_id="restart_fastapi_container",
        bash_command="docker restart $(docker ps -qf 'name=fastapi')",
        dag=dag
)
