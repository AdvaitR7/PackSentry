# PackSentry — Complete Setup and Operational Guide

> **Statutory Packaging Compliance System under the Legal Metrology (Packaged Commodities) Rules, 2011.**  
> Smart India Hackathon 2026.

---

## 1. System Overview & Architecture

PackSentry is an end-to-end statutory verification system. Inspectors photograph consumer packaged goods (Principal Display Panel, Back/Information Panel, and optional Side Panels) and receive an instant, legally grounded compliance audit with exact citations under the Legal Metrology (Packaged Commodities) Rules, 2011.

```mermaid
flowchart TD
    subgraph Client["Flutter Mobile App (Frontend/app)"]
        UI["3-Step Wizard: Details -> Capture -> Review & Submit"]
        POLL["Real-time Polling: GET /v1/inspections/{id}"]
        VIEW["Results View: Real Verdicts, Citations & Polygons"]
    end

    subgraph Server["FastAPI Gateway (Backend/app)"]
        API["POST /v1/inspections (Multipart Context + Images)"]
        WORKER["Single-Capacity Background Worker (asyncio.Queue)"]
        REG["In-Memory State Registry (<5ms Status Checks)"]
    end

    subgraph Pipeline["Multi-Engine Vision & Legal Pipeline"]
        PRE["OpenCV Preprocessing & EXIF Correction"]
        OCR["OCR Router: Google Cloud Vision -> PaddleOCR Fallback"]
        VLM["Selective Qwen2.5-VL Interpretation (Ollama)"]
        EXTRACT["Regex & Morphological Declaration Parsers"]
        RULES["23 Statutory Legal Metrology Rules (ADR-0001 - 0014)"]
    end

    subgraph Storage["Persistence (ADR-0013)"]
        DB[(Supabase Postgres: app schema)]
        S3["Supabase Storage: inspection-evidence (Private)"]
    end

    UI -->|Multipart Upload| API
    API --> WORKER
    WORKER --> PRE --> OCR --> VLM --> EXTRACT --> RULES
    RULES --> DB
    PRE --> S3
    POLL --> REG
    VIEW --> API
```

---

## 2. Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.10 – 3.12 | Backend service and test execution |
| **Flutter SDK** | 3.24.0+ | Mobile app build and testing |
| **Dart SDK** | 3.5.0+ | Included with Flutter |
| **Android SDK / ADB** | Platform Tools 34+ | Android deployment and USB reverse tethering |
| **Ollama** *(Optional)* | 0.3.0+ | Local selective vision interpretation with `qwen2.5vl:7b` |
| **CUDA / NVIDIA GPU** *(Optional)* | 12.0+ (8 GB+ VRAM) | Tested on RTX 5050 Laptop GPU for local PaddleOCR acceleration |

---

## 3. Backend Setup

### Step 3.1: Create and Activate Python Virtual Environment

From the repository root:

```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
```

*On Windows (PowerShell):*
```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3.2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.3: Configure Environment Variables

Copy the template to create your `.env` file:

```bash
cp .env.example .env
```

Open `Backend/.env` and configure credentials:

```bash
# 1. Supabase Postgres Connection (Optional for local testing)
DATABASE_URL=postgresql://postgres.eputttzflupbxqvvssvz:[YOUR-PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres

# 2. Supabase Storage & Gateway (Optional for local testing)
SUPABASE_URL=https://eputttzflupbxqvvssvz.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_secret_key_here

# 3. Google Cloud Vision Credentials (Optional — falls back to PaddleOCR automatically)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcp_vision_credentials.json

# 4. Ollama Daemon Host for Qwen2.5-VL
OLLAMA_HOST=http://localhost:11434
```

> **Zero-Config / Offline Developer Mode:**  
> If `DATABASE_URL` or `GOOGLE_APPLICATION_CREDENTIALS` are omitted, PackSentry automatically runs in local offline mode:
> - Inspected items persist in the **in-memory registry** and images store on local scratch disk (`/tmp/packsentry_scratch`).
> - Primary OCR automatically falls back to **local PaddleOCR**.
> - The entire pipeline functions without external cloud credentials.

---

## 4. Starting the Backend Server

### Method A: Using the Launcher Script (Linux / macOS)

```bash
cd Backend
bash run_backend.sh
```

### Method B: Direct Uvicorn Execution

```bash
cd Backend
export PYTHONPATH="..:.:$PYTHONPATH"
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Verification:

1. **Interactive API Documentation (Swagger UI):**  
   Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser.
2. **Honest Readiness Health Check:**  
   Open [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz). You will see real-time dependency status:
   ```json
   {
     "status": "ok",
     "database": {"connected": false, "reason": "DATABASE_URL not configured"},
     "storage": {"configured": false},
     "cloud_vision": {"configured": false, "credentials_path_set": false},
     "paddleocr": {"importable": true},
     "ollama": {"reachable": true, "resident": true, "model": "qwen2.5vl:7b"}
   }
   ```

---

## 5. Frontend (Flutter) Setup & Running

### Step 5.1: Install Flutter Packages

```bash
cd Frontend/app
flutter pub get
```

### Step 5.2: Network Transport Setup (ADR-0015)

To prevent security vulnerabilities on public or venue Wi-Fi, the backend listens strictly on loopback (`127.0.0.1`). Connect your test device using one of the following methods:

#### Option 1: Android Emulator (Recommended)
The Flutter app automatically detects when it is running on an Android emulator and routes API requests to `http://10.0.2.2:8000` (the host loopback bridge). No extra configuration is needed.

#### Option 2: Physical Android Device (over USB)
1. Enable **Developer Options** and **USB Debugging** on your phone.
2. Connect your phone to your PC with a USB cable.
3. Verify connection:
   ```bash
   adb devices
   ```
4. Reverse-forward the backend port to your phone:
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```
   *Now, requests from your phone to `http://127.0.0.1:8000` automatically route directly to your host backend!*

#### Option 3: Manual Backend URL Setting in App
In the Flutter app, navigate to the **Settings** tab. You can test and override the backend URL directly at runtime.

### Step 5.3: Run the App

From `Frontend/app`:

```bash
flutter run
```

---

## 6. Building the Production Release APK

To generate a standalone APK for testing on physical devices:

```bash
cd Frontend/app
flutter build apk --release
```

The compiled release artifact will be generated at:
```
Frontend/app/build/app/outputs/flutter-apk/app-release.apk
```

To install directly to a connected USB phone:
```bash
adb install -r build/app/outputs/flutter-apk/app-release.apk
```

---

## 7. Quality Gates & Test Suites

PackSentry includes automated test suites locking in statutory, architectural, and operational invariants:

### 7.1 Backend Test Suite (pytest)

Make sure you have activated your virtual environment:

```bash
cd Backend
export PYTHONPATH="..:.:$PYTHONPATH"
pytest tests/ -v
```

**Key Test Suites:**
- `tests/test_golden_verdicts.py`: Evaluates every registered rule across all statutory verdict states (`COMPLIANT`, `NON_COMPLIANT`, `INDETERMINATE`, `NOT_APPLICABLE`, `NOT_EVALUATED`).
- `tests/test_absence_negative_suite.py`: Verifies ADR-0005 absence-evidence gate (unconfirmed panels downgrade missing declarations to `INSUFFICIENT_EVIDENCE`) and ADR-0004 VLM provenance taint neutralization.
- `tests/test_ocr_failover_rehearsal.py`: Simulates forced Cloud Vision outage and asserts automatic failover to PaddleOCR.
- `tests/test_rules_lint.py`: AST invariant linter ensuring no rule in `app/rules/` ever accesses `normalized_text` or geometry coordinates.
- `tests/test_retention.py`: Pruning tests for 30-day storage retention and 24-hour scratch disk cleanup.
- `tests/test_pipeline_integration.py`: End-to-end pipeline run from raw images to final verdicts.

### 7.2 Frontend Test Suite (flutter)

```bash
cd Frontend/app
flutter analyze     # Enforces 0 static warnings or lint issues
flutter test        # Runs widget, model serialization, and wizard flow tests
```

---

## 8. Background Maintenance & Utilities

### 8.1 30-Day Evidence Retention Cleanup (ADR-0015)
Removes inspection evidence older than 30 days from Supabase Storage and prunes local scratch files older than 24 hours:

```bash
cd Backend
export PYTHONPATH="..:.:$PYTHONPATH"

# Dry run (audits without deleting)
python3 -m app.tasks.retention --dry-run --days 30 --scratch-hours 24

# Live execution
python3 -m app.tasks.retention --days 30 --scratch-hours 24
```

### 8.2 VLM Hardware & Co-Residency Benchmark
Measures warm vs cold Ollama latency and verifies GPU VRAM headroom alongside PaddleOCR:

```bash
cd Backend
export PYTHONPATH="..:.:$PYTHONPATH"
python3 scripts/benchmark_vlm_coresidency.py
```

---

## 9. Troubleshooting & Common Pitfalls

| Issue | Cause | Resolution |
|---|---|---|
| **App cannot reach backend (`Connection refused`)** | Physical phone attempting to reach `127.0.0.1` without reverse port bridge. | Run `adb reverse tcp:8000 tcp:8000` with the phone connected via USB. |
| **`CUDA out of memory` / PaddleOCR crash** | GPU memory contention between Qwen2.5-VL (6.6 GB) and PaddleOCR. | PaddleOCR automatically falls back to CPU on OOM. You can also enforce CPU-only OCR by setting `CUDA_VISIBLE_DEVICES=""`. |
| **Missing declarations not flagging violation** | "All Images / Panels Captured" toggle was not switched ON. | By ADR-0005 design, missing fields on partially examined packs downgrade to `INSUFFICIENT_EVIDENCE` to avoid false accusations. Turn the toggle ON in Step 2 to confirm all panels were photographed. |
| **Google Cloud Vision 403 / Missing Credentials** | ADC JSON key is absent or expired. | The backend seamlessly switches to PaddleOCR fallback. To add credentials, see `.sensitive-docs/harness/GOOGLE_APPLICATION_CREDENTIALS.md`. |
| **`422 Unprocessable Entity` on upload** | Uploaded image is corrupted or exceeds 12 MiB cap. | Ensure images are valid JPEG/PNG/WebP under 12 MiB. |
