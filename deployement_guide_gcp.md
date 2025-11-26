# GCP Deployment Guide for the TNM Staging System

## 1. Architecture Overview

This guide details a serverless, event-driven architecture on Google Cloud Platform (GCP) to deploy the multi-agent TNM staging system. This design is scalable, cost-effective, and robust, processing reports as they arrive.

The workflow is as follows:

1. A PET-CT report in PDF format is uploaded to a **Cloud Storage** bucket.
2. The upload triggers a **Cloud Function** which contains your existing OCR/JSON extraction tool.
3. The Cloud Function processes the PDF, extracts the JSON content, and publishes it as a message to a **Pub/Sub** topic.
4. A **Cloud Run** service, which hosts the containerized multi-agent TNM application, is triggered by the new message on the Pub/Sub topic.
5. The Cloud Run application executes the staging logic, making calls to the Gemini model via the **Vertex AI API**.
6. The final structured TNM staging result is saved to a **Firestore** database for querying and analysis.

![GCP Architecture Diagram](https://storage.googleapis.com/gweb-cloudblog-publish/images/serverless-document-processing.max-1500x1500.png)
*(Image credit: Google Cloud. This diagram illustrates a similar document processing pipeline.)*

---

## 2. Step-by-Step Deployment Guide

### Step 1: Prerequisites

* A Google Cloud Platform project.
* The `gcloud` command-line tool installed and authenticated (`gcloud auth login`).
* Docker installed on your local machine.
* Python 3.10+ and Node.js (for the Cloud Function) installed locally.
* Your existing OCR/JSON extraction tool, ready to be packaged.

### Step 2: Enable APIs and Configure IAM

1. **Enable APIs:** In the GCP Console, enable the following APIs for your project:
    * Cloud Run API
    * Vertex AI API
    * Pub/Sub API
    * Cloud Storage API
    * Cloud Functions API
    * Cloud Build API
    * Artifact Registry API
    * Firestore API

2. **Create Service Account:** Create a dedicated service account for this application to follow the principle of least privilege.
    ```bash
    gcloud iam service-accounts create tnm-staging-sa --display-name="TNM Staging Service Account"
    ```

3. **Assign Roles:** Grant the necessary permissions to the service account.
    ```bash
    # Role for Cloud Run/Functions to invoke other services
    gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/run.invoker"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/pubsub.publisher"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/datastore.user" # For Firestore
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/storage.objectAdmin" # For GCS access
    ```
    *Replace `YOUR_PROJECT_ID` with your actual GCP Project ID.*

### Step 3: Set Up Cloud Storage and Pub/Sub

1. **Create GCS Buckets:**
    ```bash
    gsutil mb gs://pet-ct-reports-raw
    gsutil mb gs://tnm-staging-results
    ```

2. **Create Pub/Sub Topic:**
    ```bash
    gcloud pubsub topics create json-reports-topic
    ```

### Step 4: Deploy the OCR Tool as a Cloud Function

This assumes your OCR tool can be run from a Python script.

1. **Structure your code:** Create a directory for your function with a `main.py` and `requirements.txt`. The `main.py` file should contain a function that is triggered by a GCS event.

2. **`main.py` example:**
    ```python
    import json
    from google.cloud import pubsub_v1
    # Assume 'my_ocr_tool' is your library
    # import my_ocr_tool

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path('YOUR_PROJECT_ID', 'json-reports-topic')

    def process_pet_ct_pdf(event, context):
        """Background Cloud Function to be triggered by Cloud Storage."""
        bucket_name = event['bucket']
        file_name = event['name']
        
        print(f"Processing file: {file_name} from bucket: {bucket_name}.")

        # This is where you call your existing tool.
        # It needs to read the file from GCS and return JSON.
        # json_output = my_ocr_tool.extract_text_from_gcs(bucket_name, file_name)

        # For demonstration, using placeholder JSON
        json_output = {"findings": "Tumor is 3.5 cm.", "impression": "Stage T2a"}

        # Publish the JSON result to Pub/Sub
        future = publisher.publish(topic_path, json.dumps(json_output).encode('utf-8'))
        print(f"Published message ID: {future.result()}")
    ```

3. **Deploy the Function:**
    ```bash
    gcloud functions deploy process_pet_ct_pdf \
      --runtime python310 \
      --trigger-resource gs://pet-ct-reports-raw \
      --trigger-event google.storage.object.finalize \
      --entry-point process_pet_ct_pdf \
      --service-account=tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
    ```

### Step 5: Containerize and Deploy the TNM Multi-Agent Application

1. **Develop the FastAPI App:** Using the `execution_plan_tnm.md`, build the multi-agent system using FastAPI and LangChain. The application should have an endpoint that accepts the JSON from Pub/Sub.

2. **Create a `Dockerfile`:**
    ```Dockerfile
    FROM python:3.10-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
    ```

3. **Build and Push to Artifact Registry:**
    * First, create a repository:
        ```bash
        gcloud artifacts repositories create tnm-staging-repo --repository-format=docker --location=us-central1
        ```
    * Build and push the image:
        ```bash
        gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/tnm-staging-repo/tnm-service
        ```

4. **Deploy to Cloud Run:**
    ```bash
    gcloud run deploy tnm-staging-service \
      --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/tnm-staging-repo/tnm-service \
      --platform managed \
      --region us-central1 \
      --no-allow-unauthenticated \
      --service-account=tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
      --set-env-vars="GCP_PROJECT_ID=YOUR_PROJECT_ID,FIRESTORE_COLLECTION=tnm-results"
    ```

5. **Create Pub/Sub Trigger for Cloud Run:**
    ```bash
    gcloud run services add-iam-policy-binding tnm-staging-service \
      --member="serviceAccount:service-YOUR_PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com" \
      --role="roles/run.invoker" \
      --platform=managed \
      --region=us-central1

    gcloud pubsub subscriptions create tnm-staging-subscription \
      --topic=json-reports-topic \
      --push-endpoint=$(gcloud run services describe tnm-staging-service --platform managed --region us-central1 --format 'value(status.url)') \
      --push-auth-service-account=tnm-staging-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
    ```
    *Find `YOUR_PROJECT_NUMBER` in the GCP Console homepage.*

### Step 6: Set up Firestore

1. **Create Database:** Go to the Firestore section in the GCP Console and create a new database in Native Mode. Choose a location (e.g., `us-central`).
2. Your Cloud Run service, using the `google-cloud-firestore` Python library, will now be able to write to the collection specified in its environment variables.

### Step 7: Monitoring

Use **Google Cloud's operations suite** (formerly Stackdriver) to monitor the pipeline:
* **Cloud Logging:** View logs from all services (Cloud Function, Cloud Run) to debug issues.
* **Cloud Monitoring:** Create dashboards to track the number of processed documents, execution times, and error rates.
* **Pub/Sub Monitoring:** Check the number of undelivered messages in your subscription to identify processing backlogs.
