# 📚 ScholarPulse: AI-Assisted Research Literature Filter

**ScholarPulse** is a powerful tool designed to streamline scientific literature reviews. It automatically fetches article metadata from **Crossref** or imports from **Scopus CSV**, filters them by journal ranking (**SJR Q1-Q4**), and uses **LLMs** (Local or Remote) to verify relevance to your specific research area.

![Screenshot](https://via.placeholder.com/800x400?text=ScholarPulse+Dashboard) <!-- Placeholder for a real screenshot if available -->

## 🌟 Key Features
- **Dual Data Sources**: Search live via **Crossref API** or upload a **Scopus CSV** export.
- **Advanced Journal Ranking**: Automatically identifies the best SJR quartile (Q1-Q4) for each journal, even for multi-category publications.
- **AI-Assisted Filtering**: Uses LLMs (Ollama for local, OpenRouter for remote) to scan titles and abstracts for semantic relevance.
- **Batch Processing**: Handles large searches with robust deep-paging logic (up to 3,000,000 results).
- **Interactive Dashboard**: Built with Streamlit for a user-friendly, real-time experience.
- **Data Persistence**: Automatically saves both raw and filtered results to Excel.

## 🛠 Setup & Installation

### 1. Prerequisites
- **Python 3.10+**
- **Ollama** (optional, for local LLM mode)
- **SJR Ranking File**: Place a `journal_rankings.csv` (SJR format) in the project root.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory:
```env
# LLM Configuration
LLM_MODE="local" # or "remote"
LOCAL_LLM_MODEL="gemma3:27b"
REMOTE_LLM_MODEL="google/gemini-2.0-flash-lite"
OPENROUTER_API_KEY="your_api_key"

# Crossref Configuration (Polite Pool)
CROSSREF_EMAIL="your_email@domain.com"
```

## 🚀 Usage

### Option A: Interactive Dashboard (Recommended)
Run the Streamlit application:
```bash
streamlit run app.py
```
This opens a web interface where you can:
1. Select your data source (Crossref or Scopus).
2. Configure LLM settings and journal filters.
3. Enter keywords and a research area description.
4. Monitor progress and view/export results.

### Option B: Command Line Interface
Run the CLI for quick scans:
```bash
python main.py --keywords "2D magnets" --field "2D magnetic materials and vdW heterostructures" --max 100 --mode local
```

## 📂 Project Structure
- `app.py`: Main Streamlit dashboard.
- `main.py`: CLI entry point.
- `crossref_client.py`: Handles high-performance Crossref API retrieval.
- `scopus_handler.py`: Parses Scopus CSV exports.
- `journal_ranker.py`: Matches journals against SJR rankings.
- `llm_verifier.py`: Integrates with Ollama and OpenRouter for AI verification.

## 📄 License
This project is for research/academic use. Ensure compliance with Crossref and Scopus Terms of Service.
