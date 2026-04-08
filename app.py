import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import io
import os
from datetime import date
from dotenv import load_dotenv

from crossref_client import CrossrefClient
from journal_ranker import JournalRanker
from llm_verifier import LLMVerifier
from scopus_handler import ScopusHandler

from dotenv import load_dotenv, set_key

# 1. Page Config & Styling
st.set_page_config(page_title="ScholarPulse Dashboard", page_icon="📚", layout="wide")
load_dotenv()

st.title("📚 ScholarPulse: AI Assisted Literature Filter")
st.markdown("Filter scientific articles by journal ranking (SJR) and verify relevance using LLMs.")

# 2. Sidebar Configuration
st.sidebar.header("🛠 Settings")

# Load initial values from .env
env_path = ".env"
initial_mode = os.getenv("LLM_MODE", "local")
initial_local_model = os.getenv("LOCAL_LLM_MODEL", "gemma3:27b")
initial_remote_model = os.getenv("REMOTE_LLM_MODEL", "google/gemini-2.5-flash-lite")
initial_email = os.getenv("CROSSREF_EMAIL", "lebertbill@gmail.com")
initial_api_key = os.getenv("OPENROUTER_API_KEY", "")

# LLM Mode and Model selection
llm_mode = st.sidebar.selectbox("LLM Mode", options=["local", "remote"], index=0 if initial_mode == "local" else 1)

if llm_mode == "local":
    llm_model = st.sidebar.text_input("Local Model (Ollama)", value=initial_local_model)
    st.sidebar.info("Ensure Ollama is running locally.")
    remote_model_persisted = initial_remote_model
else:
    llm_model = st.sidebar.text_input("Remote Model (OpenRouter)", value=initial_remote_model)
    local_model_persisted = initial_local_model
    api_key = st.sidebar.text_input("OpenRouter API Key", value=initial_api_key, type="password")
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key

crossref_email = st.sidebar.text_input("Crossref Email", value=initial_email)
if crossref_email:
    os.environ["CROSSREF_EMAIL"] = crossref_email

# Save Button
if st.sidebar.button("💾 Save Settings to .env", help="Save these settings permanently for future use."):
    set_key(env_path, "LLM_MODE", llm_mode)
    if llm_mode == "local":
        set_key(env_path, "LOCAL_LLM_MODEL", llm_model)
        set_key(env_path, "REMOTE_LLM_MODEL", initial_remote_model)
    else:
        set_key(env_path, "LOCAL_LLM_MODEL", initial_local_model)
        set_key(env_path, "REMOTE_LLM_MODEL", llm_model)
    
    set_key(env_path, "CROSSREF_EMAIL", crossref_email)
    if llm_mode == "remote" and api_key:
        set_key(env_path, "OPENROUTER_API_KEY", api_key)
    st.sidebar.success("Settings saved successfully!")

# Search Settings
st.sidebar.markdown("### 🌐 Data Source")
data_source = st.sidebar.radio("Choose Source", options=["Crossref API", "Scopus CSV"], index=0)
scopus_file = None
if data_source == "Scopus CSV":
    scopus_file = st.sidebar.file_uploader("Upload Scopus Export (CSV)", type=["csv"])

col_max, col_all = st.sidebar.columns([2, 1])
with col_max:
    max_results = st.number_input("Max Results", min_value=1, max_value=5000, value=50, disabled=st.session_state.get('fetch_all', False) or data_source == "Scopus CSV")
with col_all:
    st.write("") # Spacer
    fetch_all = st.checkbox("Fetch All", key='fetch_all', help="Fetch all possible results from Crossref without any limit.", disabled=data_source == "Scopus CSV")

# Filter Settings
st.sidebar.subheader("🎯 Filtering")
selected_quartiles = st.sidebar.multiselect("Journal Quartiles (SJR)", options=["Q1", "Q2", "Q3", "Q4"], default=["Q1", "Q2"])

current_year = date.today().year
year_range = st.sidebar.slider("Publication Year Range", min_value=1900, max_value=current_year, value=(2015, current_year))

# History / Load Previous Results
st.sidebar.divider()
st.sidebar.subheader("📜 History")
history_files = [f for f in os.listdir(".") if f.startswith("scholarpulse_") and f.endswith(".xlsx")]
history_files.sort(key=os.path.getmtime, reverse=True)

selected_history = st.sidebar.selectbox("Load Previous Results", options=["None"] + history_files)

# 3. Helpers
def display_results(df, total_retrieved=None, title_suffix=""):
    """Displays metrics, table, and plot for a given dataframe."""
    if df.empty and total_retrieved is None:
        st.info("No relevant articles found.")
        return

    # Metrics
    if total_retrieved is None and not df.empty and '_total_retrieved' in df.columns:
        total_retrieved = df['_total_retrieved'].iloc[0]

    m1, m2 = st.columns(2)
    m1.metric("Retrieved (Crossref)", total_retrieved if total_retrieved is not None else "N/A")
    m2.metric("Relevant (LLM)", len(df))

    st.subheader("📄 Results Table")
    # Remove metadata and internal columns for cleaner display
    display_df = df.drop(columns=['_total_retrieved']) if '_total_retrieved' in df.columns else df
    cols_to_show = ['year', 'quartile', 'journal', 'title', 'is_relevant']
    # Filter columns to only those that exist
    cols_to_show = [c for c in cols_to_show if c in display_df.columns]
    st.dataframe(display_df[cols_to_show], use_container_width=True)

    st.subheader("📊 Analysis Chart")
    year_counts = df['year'].value_counts().reset_index()
    year_counts.columns = ['Year', 'Count']
    year_counts = year_counts.sort_values('Year')
    
    fig = px.bar(year_counts, x='Year', y='Count', 
                title=f"Relevant Articles Distribution {title_suffix}",
                color_discrete_sequence=['#ff4b4b'])
    st.plotly_chart(fig, use_container_width=True)

# 4. Main Input Area
if data_source == "Crossref API":
    col1, col2 = st.columns([1, 1])
    with col1:
        keywords = st.text_input("🔍 Search Keywords", placeholder="e.g., 2D magnets, Perovskite cells")
    with col2:
        search_field = st.text_area("📖 Research Area Description", placeholder="Describe your research area for AI assisted filtering", height=68)
else:
    # Scopus Mode: Keywords not needed for search, but field is needed for LLM
    search_field = st.text_area("📖 Research Area Description", placeholder="Describe your research area for AI assisted filtering", height=68)
    # Internally use filename as keywords for naming saved files
    keywords = scopus_file.name.replace(".csv", "") if scopus_file else "Scopus_Import"

# 5. Processing Logic
async def run_scholar_pulse(keywords, field, max_res, mode, model, quartiles, years, fetch_all_active, source="Crossref API", s_file=None):
    client = CrossrefClient()
    ranker = JournalRanker()
    verifier = LLMVerifier(mode=mode, model=model)
    
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    # Sub-status for counts
    count_placeholder = st.empty()
    
    if source == "Crossref API":
        status_text.text("Searching Crossref...")
        progress_bar.progress(10)
        raw_articles = await client.search_articles(keywords, max_results=max_res, fetch_all=fetch_all_active, year_range=years)
    else:
        status_text.text("Parsing Scopus CSV...")
        progress_bar.progress(10)
        handler = ScopusHandler()
        # Save uploaded file to a temporary location for pandas to read if it's a Streamlit UploadedFile
        if s_file is not None:
            # We can pass the UploadedFile (file-like) directly to pandas if scopus_handler is updated
            # or just read it here. Let's assume ScopusHandler can take a file-like object.
             raw_articles = handler.parse_csv(s_file)
        else:
            status_text.text("No Scopus file uploaded.")
            return None, 0
    
    if not raw_articles:
        status_text.text(f"No articles found in {source}.")
        progress_bar.progress(100)
        return None, 0

    total_retrieved = len(raw_articles)
    count_placeholder.markdown(f"**Retrieved:** {total_retrieved} | **Filtered:** 0")

    # Save raw results immediately
    df_raw = pd.DataFrame(raw_articles)
    raw_filename = f"scholarpulse_{keywords.replace(' ', '_')}_raw.xlsx"
    df_raw.to_excel(raw_filename, index=False)
    st.info(f"Raw data auto-saved to `{raw_filename}`")

    status_text.text(f"Filtering {total_retrieved} articles by rank...")
    progress_bar.progress(30)
    
    filtered_articles = []
    for art in raw_articles:
        # Year check (Scopus data needs explicit year filtering if not already filtered)
        year = art.get('year')
        if year and not (years[0] <= int(year) <= years[1]):
            continue
            
        rank = ranker.get_rank(art['journal'], art['ISSNs'])
        art['quartile'] = rank or "N/A"
        if ranker.is_in_quartiles(art['journal'], art['ISSNs'], quartiles):
            filtered_articles.append(art)
            count_placeholder.markdown(f"**Retrieved:** {total_retrieved} | **Filtered:** {len(filtered_articles)}")
            
    if not filtered_articles:
        status_text.text("No articles matched the journal rank filters.")
        progress_bar.progress(100)
        return None, total_retrieved

    status_text.text(f"Verifying {len(filtered_articles)} articles with LLM...")
    final_results = []
    for i, art in enumerate(filtered_articles):
        perc = 30 + int((i / len(filtered_articles)) * 60)
        progress_bar.progress(perc)
        status_text.text(f"Verifying [{i+1}/{len(filtered_articles)}]: {art['title'][:50]}...")
        verif = await verifier.verify_relevance(art['title'], art['abstract'], field)
        art['is_relevant'] = verif.get('is_relevant', False)
        if art['is_relevant']:
            final_results.append(art)

    status_text.text(f"Processing complete! Found {len(final_results)} relevant articles.")
    progress_bar.progress(100)
    count_placeholder.empty() # Clean up the intermediate counter
    
    if final_results:
        df = pd.DataFrame(final_results)
        df['_total_retrieved'] = total_retrieved
        filename = f"scholarpulse_{keywords.replace(' ', '_')}.xlsx"
        df.to_excel(filename, index=False)
        st.success(f"Relevant results auto-saved to `{filename}`")
        return df, total_retrieved
    return None, total_retrieved

# 6. Dashboard Output
if selected_history != "None":
    st.info(f"Viewing historical results from: `{selected_history}`")
    df_history = pd.read_excel(selected_history)
    display_results(df_history, title_suffix=f"(Loaded from {selected_history})")
else:
    if st.button("🚀 Run ScholarPulse", use_container_width=True):
        if not keywords or not search_field:
            st.warning("Please provide both keywords and a research field description.")
        elif data_source == "Scopus CSV" and scopus_file is None:
            st.warning("Please upload a Scopus CSV file.")
        else:
            with st.spinner("Processing..."):
                df_results, total_retrieved = asyncio.run(run_scholar_pulse(
                    keywords, search_field, max_results, llm_mode, llm_model, 
                    selected_quartiles, year_range, fetch_all,
                    source=data_source, s_file=scopus_file
                ))
                if df_results is not None:
                    display_results(df_results, total_retrieved=total_retrieved, title_suffix=f"({keywords})")

# 7. Footer
st.divider()
st.caption("ScholarPulse | Automated Literature Review Tool")
