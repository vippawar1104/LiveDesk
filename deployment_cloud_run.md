# Deploying to Google Cloud Run

This guide explains how to deploy the Gemini Live demo application to Google Cloud Run.

## Prerequisites

1.  **Google Cloud Project**: Have an active Google Cloud project.
2.  **Google Cloud CLI**: Install and initialize the [gcloud CLI](https://cloud.google.com/sdk/docs/install).
3.  **Gemini API Key**: Obtain an API key from [Google AI Studio](https://aistudio.google.com/).

## Setup Instructions

### 1. Enable APIs

Enable the required APIs in your project:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

### 2. Store your API key in Secret Manager

Store your Gemini API key securely using Secret Manager:

```bash
echo -n "$(grep GEMINI_API_KEY .env | cut -d '=' -f2)" | gcloud secrets create GEMINI_API_KEY --data-file=-
```

### 3. Deploy to Cloud Run

Run the following command from the root of the repository to build and deploy the application:

```bash
gcloud run deploy gemini-live-demo \
    --source . \
    --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest \
    --set-env-vars MODEL=gemini-3.1-flash-live-preview \
    --allow-unauthenticated \
    --region us-central1
```

> [!TIP]
> The `MODEL` env var is optional and defaults to `gemini-3.1-flash-live-preview`.

### 4. Access the Application

Once the deployment completes, the gcloud CLI will provide a Service URL (e.g., `https://gemini-live-demo-xxxx-uc.a.run.app`). Open this URL in your browser to interact with the demo.

## Local Testing with Docker

Before deploying, you can test the container locally:

```bash
# Build the image
docker build -t gemini-live-demo .

# Run the container
docker run -p 8080:8080 \
    -e GEMINI_API_KEY=YOUR_API_KEY \
    -e PORT=8080 \
    gemini-live-demo
```
