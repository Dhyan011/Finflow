"""
Airflow stub DAG: transaction_processing_pipeline

This DAG represents the future Airflow pipeline that will replace the
synchronous HTTP call in the processing service. For now it is a
stub that demonstrates the intended workflow structure.

Tasks (planned):
  1. validate_transaction  — fetch transaction details and validate
  2. run_fraud_check       — call external fraud scoring service
  3. update_status         — PATCH account-service internal endpoint
  4. notify                — send event to notification topic
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "finflow",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def _validate_transaction(**context) -> None:
    """Stub: validate that the transaction exists and is in PENDING state."""
    transaction_id = context["dag_run"].conf.get("transaction_id")
    print(f"[STUB] Validating transaction {transaction_id}")


def _run_fraud_check(**context) -> None:
    """Stub: call fraud scoring service and raise on high-risk score."""
    transaction_id = context["dag_run"].conf.get("transaction_id")
    print(f"[STUB] Running fraud check for {transaction_id}")


def _update_status(**context) -> None:
    """Stub: PATCH account-service to mark transaction COMPLETED."""
    transaction_id = context["dag_run"].conf.get("transaction_id")
    print(f"[STUB] Updating status for {transaction_id} → COMPLETED")


def _notify(**context) -> None:
    """Stub: publish notification event to Kafka."""
    transaction_id = context["dag_run"].conf.get("transaction_id")
    print(f"[STUB] Notifying for {transaction_id}")


with DAG(
    dag_id="transaction_processing_pipeline",
    default_args=default_args,
    description="FinFlow transaction processing pipeline (stub)",
    schedule_interval=None,  # triggered externally
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finflow", "transactions"],
) as dag:

    validate = PythonOperator(
        task_id="validate_transaction",
        python_callable=_validate_transaction,
    )

    fraud_check = PythonOperator(
        task_id="run_fraud_check",
        python_callable=_run_fraud_check,
    )

    update_status = PythonOperator(
        task_id="update_status",
        python_callable=_update_status,
    )

    notify = PythonOperator(
        task_id="notify",
        python_callable=_notify,
    )

    validate >> fraud_check >> update_status >> notify
