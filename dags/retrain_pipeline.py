from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.smtp.operators.smtp import EmailOperator
from datetime import datetime
import os
    
EMAIL_USER = os.getenv("EMAIL_USER", "tatsiana.kublashvili@gmail.com")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

def extract_data():
    print("Сбор данных из источника...")

def train_model():
    print("Обучение модели...")

def evaluate_model():
    print("Оценка качества модели...")

def deploy_model():
    print("Публикация новой версии модели...")

with DAG(
    "ml_retrain_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="@hourly",
    catchup=False,
    tags=["mlops", "retrain"],
) as dag:

    extract = PythonOperator(
        task_id="extract_data",
        python_callable=extract_data,
    )

    train = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
    )

    evaluate = PythonOperator(
        task_id="evaluate_model",
        python_callable=evaluate_model,
    )

    deploy = PythonOperator(
        task_id="deploy_model",
        python_callable=deploy_model,
    )

    notify_email = EmailOperator(
        task_id="notify_success",
        from_email=EMAIL_USER, # Отправка от самого себя по-умолчанию
        to=EMAIL_USER,
        subject="✅ ML Retrain Pipeline Completed",
        html_content=f"Новая модель {MODEL_VERSION} успешно обучена и развернута.",
        conn_id="my_smtp",
    )

    extract >> train >> evaluate >> deploy >> notify_email