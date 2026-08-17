# BuildSense Deployment Guide

This document outlines the steps to run BuildSense locally for development and testing, along with details for production deployment.

---

## 1. Local Development Setup

Follow these steps to configure and run the frontend and backend applications on your local machine.

### Prerequisites

Ensure you have the following installed:
* **Python 3.11+**
* **Node.js 18+** and **npm**
* **Git**
* **PowerShell** (Windows) or a Bash-compatible shell (macOS/Linux)

---

### Step 1: Clone the Repository & Configure Environment

1. Clone the repository and navigate to the project root.
2. Copy the example environment file to create your local configurations:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Open the newly created `.env` file and set the required keys. 
   
   > [!NOTE]
   > The backend supports **local fallbacks** (in-memory SQLite/dictionary database and in-memory mock Redis) when Postgres or Redis are unreachable. You do not need active Redis or Postgres instances to run locally.

---

### Step 2: Bring Up the Backend API

The backend is built with FastAPI and runs on port `8001` by default.

1. Navigate to the backend directory:
   ```powershell
   cd apps/api
   ```
2. Create a Python virtual environment:
   ```powershell
   python -m venv .venv
   ```
3. Activate the virtual environment:
   * **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   * **macOS/Linux (Bash)**:
     ```bash
     source .venv/bin/activate
     ```
4. Install backend dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Run the FastAPI application using Uvicorn:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
   ```

---

### Step 3: Bring Up the Frontend

The frontend is a Next.js application running on port `3000` by default.

1. Open a new terminal and navigate to the frontend directory:
   ```powershell
   cd apps/web
   ```
2. Install npm dependencies:
   ```powershell
   npm install
   ```
3. Run the development server:
   ```powershell
   npm run dev -- --hostname 127.0.0.1 --port 3000
   ```

---

### Step 4: Accessing the Application

Once both servers are running, access the services at the following URLs:

* **BuildSense Web Application**: [http://127.0.0.1:3000](http://127.0.0.1:3000)
* **Backend Health Check**: [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)
* **Local Telemetry & Run Viewer**: [http://127.0.0.1:3000/en/dev/telemetry](http://127.0.0.1:3000/en/dev/telemetry)

---

### Step 5: Verification & Quality Checks

Run these commands to verify that your local environment is correctly configured and working.

#### Backend Verification
Execute these commands from `apps/api`:
* Run all unit and integration tests:
  ```powershell
  pytest tests/ -v
  ```
* Run FastMCP tool checks:
  ```powershell
  pytest tests/test_mcp_tools.py -v
  ```
* Run LLM evals (requires valid API key configurations):
  ```powershell
  pytest evals/ -v --run-evals
  ```
* Check code types and signatures:
  ```powershell
  mypy app/
  ```

#### Frontend Verification
Execute these commands from `apps/web`:
* Run TypeScript compiler checks:
  ```powershell
  npm run type-check
  ```
* Run linter:
  ```powershell
  npm run lint
  ```

---

## 2. Production Deployment (Planned)

> [!IMPORTANT]
> The production infrastructure and CI/CD pipelines will be fully implemented and configured once the application development is finalized. Below is the proposed target architecture.

### Production Stack Overview
* **Hosting Platforms**:
  * **Frontend**: Next.js deployed on Vercel or as a containerized task on AWS ECS Fargate.
  * **Backend**: FastAPI app containerized and hosted on AWS ECS Fargate.
* **Databases & Services**:
  * **Database**: PostgreSQL with `pgvector` hosted via Neon or Supabase.
  * **Cache & Rate Limiting**: Redis hosted via Upstash.
* **CI/CD Pipeline**:
  * Automated testing and Docker container build/push triggers on Git repository updates.
