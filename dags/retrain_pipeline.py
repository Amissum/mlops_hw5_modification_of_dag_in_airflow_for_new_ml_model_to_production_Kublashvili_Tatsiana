
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.smtp.operators.smtp import EmailOperator
from datetime import datetime
import os
import pickle
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Константы
EMAIL_USER = os.getenv("EMAIL_USER")
MODEL_VERSION = os.getenv("MODEL_VERSION", "Unknown")
ARTIFACT_PATH = "/tmp/airflow_hw5"
os.makedirs(ARTIFACT_PATH, exist_ok=True)

def extract_data(**kwargs):
    print("Сбор данных (Iris dataset)...")
    data = load_iris()
    X, y = data.data, data.target
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Сохраняем данные во временные файлы
    with open(f"{ARTIFACT_PATH}/X_train.pkl", "wb") as f: pickle.dump(X_train, f)
    with open(f"{ARTIFACT_PATH}/X_test.pkl", "wb") as f: pickle.dump(X_test, f)
    with open(f"{ARTIFACT_PATH}/y_train.pkl", "wb") as f: pickle.dump(y_train, f)
    with open(f"{ARTIFACT_PATH}/y_test.pkl", "wb") as f: pickle.dump(y_test, f)
    print("Данные подготовлены и сохранены.")

def train_model(**kwargs):
    print("Обучение модели (LogisticRegression)...")
    with open(f"{ARTIFACT_PATH}/X_train.pkl", "rb") as f: X_train = pickle.load(f)
    with open(f"{ARTIFACT_PATH}/y_train.pkl", "rb") as f: y_train = pickle.load(f)

    model = LogisticRegression(max_iter=200)
    model.fit(X_train, y_train)

    with open(f"{ARTIFACT_PATH}/model.pkl", "wb") as f: pickle.dump(model, f)
    print("Модель обучена и сохранена.")

def evaluate_model(**kwargs):
    print("Оценка качества модели...")
    with open(f"{ARTIFACT_PATH}/X_test.pkl", "rb") as f: X_test = pickle.load(f)
    with open(f"{ARTIFACT_PATH}/y_test.pkl", "rb") as f: y_test = pickle.load(f)
    with open(f"{ARTIFACT_PATH}/model.pkl", "rb") as f: model = pickle.load(f)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Accuracy: {accuracy}")

    # Передаем метрику в XCom
    kwargs['ti'].xcom_push(key='model_accuracy', value=accuracy)

def check_metrics(**kwargs):
    accuracy = kwargs['ti'].xcom_pull(key='model_accuracy', task_ids='evaluate_model')
    print(f"Проверка метрики: {accuracy}")
    if accuracy >= 0.85:
        return 'deploy_model'
    else:
        return 'notify_low_metrics'

def deploy_model(**kwargs):
    print(f"Публикация модели версии {MODEL_VERSION}...")
    # Здесь код деплоя

def skip_notification(**kwargs):
    print("EMAIL_USER не задан. Уведомление не отправлено.")

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

    check_metrics_task = BranchPythonOperator(
        task_id="check_metrics",
        python_callable=check_metrics,
    )

    deploy = PythonOperator(
        task_id="deploy_model",
        python_callable=deploy_model,
    )

    if EMAIL_USER:
        notify_success = EmailOperator(
            task_id="notify_success",
            from_email=EMAIL_USER,
            to=EMAIL_USER,
            subject="✅ ML Pipeline Success",
            html_content=f"Модель {MODEL_VERSION} успешно прошла проверку и развернута.",
            conn_id="my_smtp",
        )

        notify_low_metrics = EmailOperator(
            task_id="notify_low_metrics",
            from_email=EMAIL_USER,
            to=EMAIL_USER,
            subject="⚠️ ML Pipeline Skipped",
            html_content=f"Деплой модели {MODEL_VERSION} отменен. Accuracy ниже порога 0.85.",
            conn_id="my_smtp",
        )
    else:
        notify_success = PythonOperator(
            task_id="notify_success",
            python_callable=skip_notification,
        )

        notify_low_metrics = PythonOperator(
            task_id="notify_low_metrics",
            python_callable=skip_notification,
        )

    # Определение порядка выполнения
    extract >> train >> evaluate >> check_metrics_task
    check_metrics_task >> deploy >> notify_success
    check_metrics_task >> notify_low_metrics
