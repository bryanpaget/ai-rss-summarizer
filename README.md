# RSS Prediction App

## **Overview**
The RSS Prediction App is a Kubernetes-deployable system that fetches, processes, and summarizes RSS feed data from multiple sources. It uses **Large Language Models (LLMs)** to analyze trends, summarize content, and predict emerging topics over daily, weekly, and monthly timeframes. The predictions and summaries are served through an API, which can be integrated with frontend applications.

---

## **Features**
1. **RSS Fetching and Processing**  
   - Aggregates RSS feeds from multiple sources.
   - Summarizes content over different timeframes (hourly, daily, weekly, monthly).
   
2. **Prediction and Trend Analysis**  
   - Uses LLMs to predict upcoming trends based on historical feed data.

3. **Kubernetes Deployment**  
   - Scalable, containerized microservices.
   - Integrated with Kubernetes for seamless deployment and scaling.

4. **API for Access**  
   - Exposes endpoints to fetch summaries, predictions, and historical trends.

---

## **System Components**
This project comprises the following major components:

### **1. RSS Fetcher and Summarizer**
Handles the fetching of RSS feeds, parsing, and generating summarized data over various timeframes.  
- **File:** `rss_service.py`  
- **Dockerfile:** `Dockerfile` (for RSS Fetcher)  
- **Endpoints:**  
  - `/fetch`: Fetches and stores RSS feeds.  
  - `/summarize`: Summarizes data for specific timeframes (e.g., daily, weekly).

---

### **2. LLM Prediction Service**
Generates predictions for emerging trends using historical RSS data and pre-trained Large Language Models.  
- **File:** `llm_service.py`  
- **Dockerfile:** `Dockerfile` (for LLM Prediction)  
- **Endpoints:**  
  - `/predict`: Accepts RSS metadata and generates trend predictions.

---

### **3. Unified API**
A single API that integrates the RSS fetcher and prediction functionalities. This service acts as the primary interface for the app.  
- **File:** `main_service.py`  
- **Dockerfile:** `Dockerfile` (for Unified API)  
- **Endpoints:**  
  - `/fetch`: Fetches RSS feeds.  
  - `/summarize`: Returns summaries for the past hour, day, week, or month.  
  - `/predict`: Provides predictions for upcoming trends (daily, weekly, monthly).

---

### **4. Kubernetes Deployment**
The application is packaged as a Helm chart to deploy in Kubernetes.

#### **Key Files in Helm Chart:**
- **`Chart.yaml`:** Metadata for the Helm chart.  
- **`values.yaml`:** Configurable parameters for the deployment, such as replicas, resource limits, and image tags.  
- **`templates/deployment.yaml`:** Kubernetes deployment definition for the app.  
- **`templates/service.yaml`:** Exposes the app as a service within the cluster.  
- **`templates/ingress.yaml`:** Configures Ingress for external access.  
- **`templates/hpa.yaml`:** Sets up autoscaling based on resource utilization.  

---

## **File Descriptions**

### **Root Directory**
- **`requirements.txt`:** Python dependencies for all services.
- **`Dockerfile`:** Generic Dockerfile for all services (customized for each service in subdirectories).
- **`README.md`:** This file, explaining the system and usage.

### **Helm Chart Directory (`rss-prediction-app/`)**
- **`Chart.yaml`:** Describes the application for Helm.  
- **`values.yaml`:** Default values for configuring replicas, resources, and service settings.  
- **`templates/`:** Contains Kubernetes YAML templates for deployments, services, ingress, and HPA.

---

## **Installation and Usage**

### **1. Prerequisites**
- Python 3.9+
- Docker
- Kubernetes cluster
- Helm 3+

### **2. Build Docker Images**
Build the Docker images for the services and push them to a container registry:
```bash
# Build RSS Fetcher Service
docker build -t your-dockerhub-username/rss-fetcher-service -f Dockerfile .

# Build LLM Prediction Service
docker build -t your-dockerhub-username/llm-prediction-service -f Dockerfile .
```
Push the images:
```bash
docker push your-dockerhub-username/rss-fetcher-service
docker push your-dockerhub-username/llm-prediction-service
```

### **3. Deploy with Helm**
Package and deploy the application using Helm:
```bash
helm install rss-prediction ./rss-prediction-app
```

### **4. Access the API**
Once deployed, access the API via the Ingress controller or using port-forwarding:
```bash
kubectl port-forward service/rss-prediction 8000:80
```
- Access summaries: `http://localhost:8000/summarize`
- Access predictions: `http://localhost:8000/predict`

---

## **API Overview**

### **Endpoints**
#### **RSS Fetcher and Summarizer**
- **GET `/fetch`**  
   Fetches and processes RSS feeds.  
   **Response:** Status of fetching and list of new feeds added.

- **GET `/summarize?timeframe=[hour|day|week|month]`**  
   Returns summarized data for the specified timeframe.  
   **Response:** Summary text or JSON.

#### **Prediction Service**
- **POST `/predict`**  
   Accepts historical data and returns predictions for the next period.  
   **Payload Example:**
   ```json
   {
       "historical_data": "Summarized feed data for the past week...",
       "timeframe": "weekly"
   }
   ```
   **Response:** Predicted trends or topics.

---

## **Future Enhancements**
1. **Advanced Monitoring:** Add Prometheus metrics for detailed service insights.
2. **Frontend Integration:** Develop a calendar-style UI for visualizing summaries and predictions.
3. **Real-Time Updates:** Use Kafka or RabbitMQ for streaming new feed data in real-time.
4. **Vector Database:** Integrate with Pinecone or Weaviate for semantic similarity searches.
