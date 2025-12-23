# MLOps HW5: Airflow Retrain Pipeline

Этот проект содержит DAG для Apache Airflow, который автоматизирует процесс переобучения ML-модели (Logistic Regression на датасете Iris), проверки метрик и условного деплоя/уведомления.

## 1. Установка зависимостей

Для работы пайплайна необходимо установить Apache Airflow и библиотеки для ML:

```bash
pip install apache-airflow scikit-learn pandas
```

## 2. Настройка окружения

Перед запуском Airflow необходимо задать переменные окружения, которые используются в DAG для конфигурации и уведомлений.

```bash
# Email для уведомлений (отправитель и получатель)
export EMAIL_USER="your_email@gmail.com"

# Версия модели (используется в логах и уведомлениях)
export MODEL_VERSION="1.0.0"
```

*Примечание: Если `EMAIL_USER` не задан, DAG будет пропускать отправку писем, выводя сообщение в лог.*

## 3. Запуск Airflow

Для локальной разработки и тестирования удобнее всего использовать режим `standalone`:

```bash
airflow standalone
```

Эта команда запустит базу данных, веб-сервер (по умолчанию на port 8080) и планировщик.
Пароль для входа в UI (пользователь `admin`) будет выведен в терминале или сохранен в файле `standalone_admin_password.txt`.

## 4. Настройка SMTP подключения (Gmail)

Для отправки уведомлений используется подключение с ID `my_smtp`.
**Важно:** Из-за особенностей `SmtpHook` в текущих версиях провайдера, для порта 465 (SSL) требуются специфические параметры `extra`.

### Способ 1: Через веб-интерфейс Airflow
1. Перейдите в **Admin** -> **Connections**.
2. Нажмите **+** (Create).
3. Заполните поля:
   - **Connection Id**: `my_smtp`
   - **Connection Type**: `SMTP`
   - **Host**: `smtp.gmail.com`
   - **Login**: `your_email@gmail.com`
   - **Password**: `your_app_password` (для Google Mail - App Password, не основной пароль от аккаунта)
   - **Port**: `465`
   - **Extra**: `{"disable_tls": true, "disable_ssl": false}`

### Способ 2: Через код на Python
```python
import json
from airflow.models import Connection
from airflow import settings

conn = Connection(
    conn_id="my_smtp",
    conn_type="smtp",
    host="smtp.gmail.com",
    port=465,
    login="your_email@gmail.com",
    password="your_app_password",
    extra=json.dumps({"disable_tls": True, "disable_ssl": False})
)

session = settings.Session()
session.add(conn)
session.commit()
session.close()
```

## 5. Деплой DAG

Файл пайплайна находится в `dags/retrain_pipeline.py`. Для того чтобы Airflow его увидел, файл нужно поместить в папку DAGs (обычно `~/airflow/dags`).

```bash
mkdir -p ~/airflow/dags
cp dags/retrain_pipeline.py ~/airflow/dags/
```

После копирования DAG должен появиться в веб-интерфейсе Airflow в течение минуты.

## 6. Логика работы DAG (`ml_retrain_pipeline`)

1. **extract_data**: Загружает датасет Iris, делит на train/test и сохраняет во временную папку.
2. **train_model**: Обучает `LogisticRegression` и сохраняет модель.
3. **evaluate_model**: Проверяет модель на тестовой выборке. Результат (Accuracy) сохраняется в XCom.
4. **check_metrics** (Branching):
   - Если `Accuracy >= 0.85` -> переход к **deploy_model**.
   - Если `Accuracy < 0.85` -> переход к **notify_low_metrics** (деплой пропускается).
5. **deploy_model**: Симуляция деплоя.
6. **notify_success** / **notify_low_metrics**: Отправка email (или лог, если email не настроен).
