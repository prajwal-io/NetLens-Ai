
# NetSight AI
### Intelligent Network Traffic Analyser Using Machine Learning

> **Project Status:** Planning and Development
> **Development:** Primarily Solo
> **Target Completion:** November 10, 2026
> **Mini-Project Submission:** November 21, 2026
> **Domain:** Computer Networks + Machine Learning

## 1. Project Overview

NetSight AI is a web-based intelligent network traffic analysis platform that uses Machine Learning to analyze network communication, classify network traffic, identify potentially malicious activities, and visualize results through an interactive dashboard.

Traditional network monitoring tools often require manual packet inspection and predefined rules. NetSight AI aims to simplify the process by bringing traffic analysis, machine learning, investigation, and visualization into one unified interface.

The application is designed to make network traffic understandable, interactive, and accessible.

### Core Idea

Instead of showing users thousands of raw network records, NetSight AI processes compatible traffic data, runs it through a trained Machine Learning model, and presents meaningful insights through visualizations and reports.

**Core workflow:**

1. Collect or upload network traffic data.
2. Validate and preprocess the dataset.
3. Extract relevant network traffic features.
4. Analyze traffic using a trained ML model.
5. Classify traffic as normal or potentially malicious.
6. Visualize network activity and classification results.
7. Investigate suspicious traffic.
8. Generate downloadable analysis reports.

The project will include a historical traffic replay system for an interactive demonstration.

**Important:** Historical replay is not the same as real-time packet capture. The application must accurately label its data sources and detection modes.

---

## 2. Academic Project Information

| Field | Details |
|---|---|
| Project | Intelligent Network Traffic Analyser Using ML |
| Application Name | NetSight AI |
| Department | Computer Science and Engineering |
| Domain | Computer Networks |
| Presented By | Vidya, Prajwal, Harini |
| Batch | Batch 11, CSE-C |
| Mentor | Dr. L. Raghavendar Raju |
| Development Approach | Primarily solo-led |
| Completion Target | November 10, 2026 |
| Submission | November 21, 2026 |

The project is based on the original academic presentation covering network traffic analysis, Machine Learning, data preprocessing, traffic classification, and results visualization.

---

## 3. Problem Statement

Modern computer networks continuously generate large volumes of data packets.

Analyzing this traffic manually becomes difficult, especially when monitoring large amounts of network communication.

Traditional approaches include:

- Manual packet inspection.
- Rule-based network monitoring.
- Statistical traffic analysis.
- Multiple separate tools for processing and visualization.

These approaches have limitations:

- Manual inspection is time-consuming.
- Rule-based systems depend on predefined conditions.
- Complex patterns can be difficult to recognize.
- Separate tools increase workflow complexity.

### Proposed Solution

Develop an ML-powered network traffic analysis platform capable of processing compatible network traffic data, identifying normal and suspicious patterns, and presenting meaningful results through an interactive web dashboard.

The system combines network traffic processing, Machine Learning, visualization, and reporting into a structured workflow.

---

## 4. Project Objectives

### Primary Objectives

1. Obtain network traffic data for analysis.
2. Validate and preprocess network traffic datasets.
3. Extract useful network traffic features.
4. Train a suitable Machine Learning algorithm.
5. Classify network flows as normal or potentially malicious.
6. Visualize traffic patterns and classifications.
7. Allow investigation of individual network records.
8. Generate useful traffic analysis reports.

### Secondary Objectives

- Create a visually engaging monitoring dashboard.
- Demonstrate historical traffic scenarios.
- Compare normal and malicious traffic patterns.
- Display model evaluation metrics.
- Build a modular architecture for future expansion.
- Prepare a reliable interactive faculty demonstration.

---

## 5. Application Modules

The website will contain six main modules connected through one consistent application interface.

### 5.1 Command Center

The Command Center is the primary dashboard.

It provides a quick overview of the application's analysis results.

**Features:**

- Total analyzed traffic flows.
- Normal traffic count.
- Suspicious traffic count.
- Traffic distribution.
- Historical traffic activity chart.
- Recent analysis history.
- Recent suspicious classifications.
- Backend connection status.
- ML model availability and version.

The dashboard should load quickly and provide clear information without overwhelming the user.

Any sample or demonstration data must be clearly labeled.

### 5.2 Network Pulse

Network Pulse is the main interactive visualization module.

It displays network activity through connected nodes, animated links, and traffic flow information.

**Features:**

- Interactive network visualization.
- Animated traffic connections.
- Normal and suspicious traffic indicators.
- Clickable network elements.
- Traffic flow details.
- Historical traffic replay.
- Play, pause, restart, and replay-speed controls.
- Normal and suspicious traffic scenarios.

**Important implementation rule:**

Display actual device relationships only when source and destination information exists in the dataset.

When the dataset lacks this information, any illustrative topology must be labeled as a conceptual visualization.

The November 10 release will focus on historical traffic replay rather than real-time packet capture.

### 5.3 Traffic Analyzer

The Traffic Analyzer allows users to upload compatible network traffic datasets and receive ML classification results.

**Features:**

- Drag-and-drop CSV upload.
- File format validation.
- Missing-column detection.
- Data type validation.
- Dataset overview.
- Analysis progress indicators.
- ML prediction results.
- Normal versus malicious traffic counts.
- Classification result table.
- CSV result export.

The frontend will send the validated dataset to the FastAPI backend.

The backend will preprocess the data using the saved training pipeline and run actual ML inference.

Do not generate fake predictions when the ML model is unavailable.

### 5.4 Threat Investigation

The Threat Investigation module allows users to examine individual classified network flows.

**Features:**

- List of potentially malicious flow records.
- Classification labels.
- Model scores when available.
- Relevant network flow features.
- Traffic record details.
- Filtering and searching.
- Explanation of model-generated classifications.

The system must distinguish actual model output from general explanatory text.

Feature importance may help interpret predictions but should not be presented as definitive proof of an attack.

### 5.5 Model Lab

Model Lab provides information about the Machine Learning system.

**Features:**

- Model name and version.
- Algorithm details.
- Dataset information.
- Number of input features.
- Training and testing information.
- Accuracy.
- Precision.
- Recall.
- F1-score.
- Confusion matrix.
- Feature importance where supported.

All displayed evaluation metrics must come from actual model testing.

No hardcoded accuracy or fabricated model performance values are permitted.

### 5.6 Reports

The Reports module allows users to export and review network traffic analysis results.

**Features:**

- Analysis summary.
- Traffic classification totals.
- Model metadata.
- Dataset information.
- Analysis timestamp.
- Suspicious flow summaries.
- CSV export.
- PDF report generation.

The exported reports must match the predictions and totals shown in the application.

---

## 6. Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Custom CSS
- React Router
- Recharts
- React Flow (@xyflow/react)
- Motion for React
- Lucide Icons

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- Pandas
- NumPy

### Machine Learning

- Scikit-learn
- Random Forest Classifier
- Logistic Regression for baseline comparison
- Pandas
- NumPy
- Joblib

### Database

- SQLite

### Reporting

- CSV export
- ReportLab for PDF generation

### Development Tools

- Git
- GitHub
- VS Code / OpenAI Codex
- Python virtual environment
- npm
- Browser developer tools

### Hosting Strategy

The application will initially run locally.

Frontend and backend will be executed as separate development services.

A cloud deployment is optional and must not block the project deadline.

The complete faculty demonstration should work without depending on internet connectivity.

---

## 7. System Architecture

```text
                    USER
                     |
                     v
             REACT FRONTEND
                     |
           Interactive Dashboard
                     |
                     v
              FASTAPI BACKEND
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
   CSV Input     Analysis API   Replay Data
       |             |             |
       +-------------+-------------+
                     |
                     v
               DATA VALIDATION
                     |
                     v
                PREPROCESSING
                     |
                     v
              FEATURE PROCESSING
                     |
                     v
               ML MODEL
             (Random Forest)
                     |
                     v
             TRAFFIC CLASSIFICATION
                     |
          +----------+----------+
          |                     |
          v                     v
     NORMAL TRAFFIC       MALICIOUS TRAFFIC
          |                     |
          +----------+----------+
                     |
                     v
              FASTAPI RESPONSE
                     |
                     v
             REACT DASHBOARD
                     |
          +----------+----------+
          |                     |
          v                     v
     VISUALIZATION         REPORT EXPORT
```

### Architecture Principles

1. Separate frontend and backend responsibilities.
2. Keep ML training separate from inference.
3. Use a consistent API contract.
4. Store model artifacts independently from application code.
5. Keep UI components reusable.
6. Validate all uploaded files.
7. Avoid unnecessary infrastructure.
8. Design for local execution first.
9. Make failures visible instead of returning invented results.

---

## 8. Machine Learning Implementation

### Dataset

Recommended dataset:

CIC-IDS2017

https://www.unb.ca/cic/datasets/ids-2017.html

This dataset provides labeled network traffic suitable for intrusion detection research.

The original academic PPT does not mandate this specific dataset. It is selected as a practical implementation recommendation.

### Initial ML Goal

Binary classification:

- Normal Traffic
- Malicious Traffic

Multiclass attack classification may be introduced later if the model produces satisfactory evaluation results.

### Proposed Algorithm

**Primary:** Random Forest Classifier

**Baseline:** Logistic Regression

Random Forest is selected because it works well with many structured tabular datasets and can represent nonlinear feature relationships.

Its performance must still be evaluated on the chosen traffic dataset.

### ML Pipeline

```text
Network Traffic CSV
        |
        v
Data Validation
        |
        v
Data Cleaning
        |
        v
Feature Selection
        |
        v
Training / Testing Split
        |
        v
Model Training
        |
        v
Model Evaluation
        |
        v
Save Trained Pipeline
        |
        v
FastAPI Inference
        |
        v
Classification Results
```

### Important Model Requirements

- Use appropriate training and testing separation.
- Avoid leakage between related traffic samples where possible.
- Handle missing and invalid values consistently.
- Preserve feature names and order.
- Store the trained preprocessing pipeline.
- Evaluate class imbalance.
- Calculate real model metrics.
- Save model metadata.
- Use held-out data for the faculty demonstration.

### Evaluation Metrics

- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix

Accuracy alone is insufficient for an imbalanced intrusion dataset.

Precision and recall for malicious traffic must also be evaluated.

### Model Limitations

The system will classify supported network-flow records.

It cannot automatically claim to:

- Detect every unknown cyberattack.
- Prevent attacks.
- Block malicious traffic.
- Detect malicious URLs.
- Identify malware files.
- Monitor networks continuously.

These capabilities require additional implementations and evaluations.

---

## 9. API Design

Base URL:

`http://127.0.0.1:8000/api/v1`

### Phase 1 API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Backend and model status |
| POST | /traffic/validate | Validate CSV input |

### Phase 2 API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /traffic/analyze | Run real ML inference |
| GET | /model/info | Return model metadata |

### Phase 3 API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /analyses | Analysis history |
| GET | /analyses/{id} | Analysis details |
| GET | /replays | Available replay scenarios |
| POST | /replays/{id}/analyze | Analyze selected replay |
| GET | /analyses/{id}/export.csv | CSV export |
| GET | /analyses/{id}/report.pdf | PDF report |

### Example Health Response

```json
{
  "status": "ok",
  "service": "netsight-api",
  "model_loaded": false,
  "model_version": null
}
```

### Example Analysis Response

The following JSON demonstrates the planned response structure. Its values are illustrative, not real ML results.

```json
{
  "analysis_id": "sample-001",
  "source_type": "uploaded_csv",
  "model_version": "rf-v1",
  "total_flows": 2,
  "counts": {
    "normal": 1,
    "malicious": 1
  },
  "predictions": [
    {
      "row_id": 1,
      "label": "normal",
      "model_score": 0.12
    },
    {
      "row_id": 2,
      "label": "malicious",
      "model_score": 0.88
    }
  ]
}
```

The meaning of `model_score` must be defined consistently during implementation.

### API Requirements

- Proper validation.
- Consistent response structures.
- Clear error messages.
- File-size restrictions.
- CSV schema validation.
- CORS configuration.
- Correct HTTP status codes.
- Proper model-loading errors.
- No fabricated predictions.

If the model has not been trained or cannot load, prediction requests should return an appropriate error such as HTTP 503.

---

## 10. Frontend Design System

### Visual Direction

Build a premium, modern, technical dashboard with a clean and distinct design identity.

Avoid generic cybersecurity templates and overused AI-generated website aesthetics.

### Theme

Primary theme: Light

### Color Palette

| Color | Hex | Usage |
|---|---|---|
| Canvas | #F7F8FA | Main background |
| Ink | #171C2A | Typography |
| Signal Blue | #3268F5 | Primary interactions |
| Threat Red | #ED554A | Suspicious traffic |
| Normal Green | #25A47A | Healthy traffic |
| White | #FFFFFF | Cards |

### Typography

- Space Grotesk: Headings
- Inter: Interface text
- Optional monospace: Technical values and network identifiers

### Layout

- Compact left sidebar.
- Consistent navigation.
- Spacious dashboard grid.
- Clearly differentiated sections.
- Responsive layout.
- High-contrast text.
- Readable charts.
- Clean data tables.

### Motion and Interaction

Use animations only when they serve an actual purpose.

Examples:

- Smooth page transitions.
- Network flow animations.
- Chart transitions.
- Interactive nodes.
- Hover details.
- Expandable alert panels.
- Replay progress indicators.
- Loading and success states.

### Design Rules

Avoid:

- Random floating gradient blobs.
- Excessive glassmorphism.
- Generic glowing cybersecurity effects.
- Unnecessary animations.
- Inconsistent spacing.
- Hardcoded fake activity counters.
- Unreadable charts.
- Excessively decorative components.

The final website should feel like a carefully designed technical product rather than a generic AI-generated dashboard.

### Trust and Transparency

Every data-driven section should communicate whether it represents:

- Sample UI Data
- Historical Replay
- Uploaded Analysis
- Actual ML Prediction

The application must never make demo-only data look like live network monitoring.

---

## 11. Repository Structure

```text
netsight-ai/
|
|-- README.md
|-- .gitignore
|
|-- frontend/
|   |-- public/
|   |-- src/
|   |   |-- app/
|   |   |-- components/
|   |   |   |-- ui/
|   |   |   |-- charts/
|   |   |   |-- network/
|   |   |-- pages/
|   |   |-- services/
|   |   |-- fixtures/
|   |   |-- types/
|   |   |-- styles/
|   |   |-- main.tsx
|   |-- .env.example
|   |-- package.json
|
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- api/
|   |   |-- schemas/
|   |   |-- services/
|   |   |-- db/
|   |   |-- core/
|   |
|   |-- ml/
|   |   |-- train.py
|   |   |-- evaluate.py
|   |   |-- artifacts/
|   |
|   |-- tests/
|   |-- .env.example
|   |-- requirements.txt
|
|-- data/
|   |-- samples/
|   |-- README.md
|
|-- docs/
|   |-- architecture.md
|   |-- model-evaluation.md
|   |-- faculty-demo.md
```

This is the planned repository structure.

Files and folders should be created as they are implemented.

Do not commit:

- Virtual environments.
- API secrets.
- Large raw datasets.
- Personal network captures.
- Generated databases containing sensitive information.

---

## 12. Local Development Setup

### Prerequisites

- Node.js
- npm
- Python 3.11 or 3.12
- Git
- VS Code or another editor

### Frontend Setup

From the project root:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

Install the selected frontend libraries and configure Tailwind CSS following their current installation instructions.

### Frontend Environment

Create `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### Backend Setup

Create the `backend` directory.

Inside it:

```bash
python -m venv .venv
```

Activate the environment.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install fastapi "uvicorn[standard]" python-multipart pydantic pandas numpy scikit-learn joblib
```

Once `backend/app/main.py` has been implemented with a FastAPI instance named `app`, start the server:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URL:

`http://127.0.0.1:8000`

Health endpoint:

`http://127.0.0.1:8000/api/v1/health`

API documentation:

`http://127.0.0.1:8000/docs`

These commands describe the initial development setup. The source files, endpoints, and ML model must still be implemented.

---

## 13. Development Roadmap

### Phase 1: Frontend and Backend Foundation

**Target: November 5–6**

Priority: Establish a working application structure.

#### Frontend Tasks

- Initialize React + TypeScript + Vite.
- Set up Tailwind CSS.
- Configure project fonts.
- Establish design tokens.
- Build application navigation.
- Build sidebar and top navigation.
- Create all six page routes.
- Build reusable UI components.
- Start the Command Center dashboard.
- Add sample-state charts and tables.
- Add loading, empty, and error states.
- Create a centralized API client.

#### Backend Tasks

- Initialize FastAPI.
- Configure local CORS.
- Build health-check endpoint.
- Create API response schemas.
- Create CSV validation endpoint.
- Add basic error handling.
- Establish folder structure for ML services.
- Prepare SQLite configuration.

#### Integration Tasks

- Connect React to FastAPI.
- Fetch backend status.
- Display actual connectivity information.
- Verify CSV validation requests.
- Test backend failures.
- Confirm the frontend does not show fake model results.

#### Phase 1 Deliverable

A polished, navigable frontend connected to a functioning FastAPI backend.

The backend does not need to have a trained ML model during this phase.

### Phase 2: Machine Learning and Inference

**Target: November 6–7**

Tasks:

- Obtain a suitable labeled traffic dataset.
- Prepare a manageable dataset subset.
- Clean and validate the data.
- Select appropriate features.
- Split training and evaluation data.
- Train a baseline model.
- Train Random Forest.
- Evaluate performance.
- Save the fitted preprocessing/model pipeline.
- Implement model loading.
- Implement inference API.
- Connect CSV analysis to the model.

Deliverable:

A working pipeline capable of returning real predictions for compatible network-flow records.

### Phase 3: Dashboard Integration

**Target: November 8**

Tasks:

- Connect actual inference results to the dashboard.
- Implement real traffic classification cards.
- Populate traffic charts.
- Build results tables.
- Complete Threat Investigation.
- Implement analysis history.
- Show model information.
- Add clear prediction and error states.

Deliverable:

A functional ML-powered traffic analysis dashboard.

### Phase 4: Replay, Reports, and Demo

**Target: November 9–10**

Tasks:

- Prepare historical traffic scenarios.
- Build replay controls.
- Connect replay data to model inference.
- Add animated network visualization.
- Complete reporting.
- Integrate CSV export.
- Implement PDF export if time allows.
- Test application stability.
- Fix critical bugs.
- Prepare an offline faculty demo.

Deliverable:

A stable demonstration-ready mini-project.

### Final Review and Submission

| Date | Activity |
|---|---|
| Nov 11–12 | First faculty review |
| Nov 13–14 | Address technical feedback |
| Nov 15–16 | Improve UI and interaction polish |
| Nov 17–18 | Complete project report and PPT |
| Nov 19 | Mock presentation |
| Nov 20 | Final testing and backup |
| Nov 21 | Mini-project submission |

The November 10 target is an aggressive MVP target. Core reliability should take precedence over optional features.

---

## 14. Faculty Demonstration Strategy

The faculty demonstration should be short, interactive, and technically verifiable.

### Demo Duration

Approximately five minutes.

### Stage 1: Normal Traffic

Time: 00:00–00:40

- Open the Command Center.
- Explain the overall system.
- Run a normal historical traffic replay.
- Display healthy network activity.
- Introduce the ML monitoring workflow.

### Stage 2: Suspicious Traffic

Time: 00:40–01:40

- Select a prepared suspicious traffic scenario.
- Replay records through the trained model.
- Display classification changes.
- Highlight suspicious results.
- Show updated traffic charts.

The replay must represent actual model processing of historical records.

### Stage 3: Threat Investigation

Time: 01:40–02:40

- Select a suspicious flow record.
- Display its network features.
- Show its predicted class.
- Explain its model score if available.
- Show how the system helps investigate traffic.

### Stage 4: Faculty Interaction

Time: 02:40–03:40

- Invite the faculty to upload a prepared compatible CSV.
- Validate the input.
- Run actual model inference.
- Display results.
- Explain the workflow.

This stage demonstrates that the project is functional rather than merely a scripted animation.

### Stage 5: Model Evaluation and Reporting

Time: 03:40–05:00

- Open Model Lab.
- Show model information.
- Explain accuracy, precision, recall, and F1-score.
- Display confusion matrix.
- Export the analysis report.
- Summarize the project's contribution.

### Demo Rules

- Use a working trained model.
- Use held-out demonstration records.
- Keep data sources clearly labeled.
- Do not simulate attacks on public or institutional networks.
- Prepare offline backups.
- Avoid fake predictions.
- Make all interactive actions functional.
- Keep the demonstration reproducible.

---

## 15. Testing Checklist

### Frontend

- [ ] All six routes work.
- [ ] Sidebar navigation functions correctly.
- [ ] Dashboard components render properly.
- [ ] Responsive layout works.
- [ ] Charts display correct information.
- [ ] Loading states work.
- [ ] Empty states work.
- [ ] Error states work.
- [ ] Network visualization is interactive.
- [ ] Demo data is correctly labeled.

### Backend

- [ ] FastAPI starts without errors.
- [ ] Health-check endpoint works.
- [ ] CORS is configured.
- [ ] CSV validation works.
- [ ] Invalid files are rejected.
- [ ] API errors are handled.
- [ ] Model loading works.
- [ ] Inference returns real results.

### Machine Learning

- [ ] Dataset preprocessing succeeds.
- [ ] Model training completes.
- [ ] Held-out evaluation is implemented.
- [ ] Model artifacts are saved.
- [ ] Inference uses the saved pipeline.
- [ ] Feature schema matches training.
- [ ] Evaluation metrics are reproducible.
- [ ] No fabricated metrics are displayed.

### Integration

- [ ] React connects to FastAPI.
- [ ] Uploaded CSV reaches the backend.
- [ ] ML predictions return to the frontend.
- [ ] Dashboard displays real results.
- [ ] Classification totals are correct.
- [ ] Investigation details match selected records.
- [ ] Replay scenarios work.
- [ ] Reports match analysis results.

### Faculty Demo

- [ ] Application works locally.
- [ ] Demo works without Wi-Fi.
- [ ] Test CSV files are prepared.
- [ ] Historical replay data is available.
- [ ] Model evaluation is ready.
- [ ] Report generation works.
- [ ] Backup demonstration is prepared.
- [ ] Presentation fits within five minutes.

---

## 16. Future Enhancements

Features outside the initial mini-project scope:

1. Authorized live packet capture.
2. PCAP file processing with compatible feature extraction.
3. Multiclass attack identification.
4. Additional anomaly-detection models.
5. Real-time alert notifications.
6. Extended analytics and comparison.
7. Authenticated multiuser accounts.
8. Long-term analysis storage.
9. Model retraining interface.
10. Advanced network topology visualization.

These are future possibilities, not features promised for November 10.

---

## 17. Responsible Use and Limitations

NetSight AI is an academic network traffic analysis project.

The application is intended for educational use, model evaluation, and authorized network traffic analysis.

Important limitations:

- ML classifications may contain false positives and false negatives.
- Model predictions are not proof of malicious behavior.
- Historical replay is not live packet monitoring.
- The system does not automatically prevent cyberattacks.
- The model is limited by its training data and features.
- Raw PCAP support requires additional processing.
- Network data should only be analyzed with appropriate authorization.

The project's results must be represented accurately.

---

## 18. References

### Academic References

1. Nguyen & Armitage (2008), Internet Traffic Classification Using Machine Learning.
2. Moore & Zuev (2005), Internet Traffic Classification Using Bayesian Analysis Techniques.
3. Sharafaldin et al. (2018), Network Intrusion Detection Datasets.
4. Boutaba et al. (2018), Machine Learning in Networking.

### Technical Resources

CIC-IDS2017:
https://www.unb.ca/cic/datasets/ids-2017.html

React:
https://react.dev/

Vite:
https://vite.dev/

FastAPI:
https://fastapi.tiangolo.com/

Scikit-learn:
https://scikit-learn.org/

React Flow:
https://reactflow.dev/

Recharts:
https://recharts.org/

---

## 19. Immediate Development Priority

Start with Phase 1.

The first working integration should be:

```text
React Dashboard
      |
      v
Frontend API Client
      |
      v
GET /api/v1/health
      |
      v
FastAPI Backend
      |
      v
Health Response
      |
      v
Real Backend Status Displayed in UI
```

After the first integration works:

1. Build CSV validation.
2. Prepare the ML dataset.
3. Train the classification model.
4. Implement real inference.
5. Connect predictions to the dashboard.
6. Complete historical replay.
7. Prepare the faculty demonstration.

### Development Principle

Build the smallest functional end-to-end workflow first.

Prioritize correct ML functionality, clean architecture, reliable integration, and thoughtful visual design.

**Project Vision: Make network traffic analysis understandable, interactive, and verifiable.**

## Phase 1 implementation

The frontend and API foundation are implemented. See [Phase 1 local run instructions](docs/phase-1.md) and [architecture and CSV contract](docs/architecture.md). Later-phase capabilities remain explicitly unavailable.


## Frontend quality update
All eight review priorities are implemented. See [quality checklist and measured audits](docs/frontend-quality.md). The production preview uses the same-origin Vite API proxy; the FastAPI contracts are unchanged. The logo now uses a derived SVG trace, and the dashboard chart uses a lightweight native SVG renderer.

## Frontend completion pass
See [the 18-area frontend checklist](docs/frontend-completion.md) for completed interactions, tests and remaining backend dependencies. The updated frontend includes a pausable background loop, session preferences, cancellable uploads, investigation filters/mobile details, network zoom/reset, real validation receipts, skeletons and error recovery.
