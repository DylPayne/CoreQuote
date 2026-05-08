import streamlit as st
import sys
import os

# Add src to path for absolute imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

st.set_page_config(
    page_title="Core Quotes",
    page_icon="📏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Navigation ─────────────────────────────────────────────────────────────────

projects_page = st.Page("pages/_Projects.py",    title="Projects",          icon="📁")
quotes_page   = st.Page("pages/_Quotes.py",      title="Quotes",            icon="📋")
detail_page   = st.Page("pages/_QuoteDetail.py", title="Quote Detail",      icon="📐")
calc_page     = st.Page("pages/_Calculator.py",  title="Cutlist Generator", icon="🔧")
slides_page   = st.Page("pages/_Slides.py",      title="Slides Library",    icon="🗂️")
boards_page   = st.Page("pages/_Boards.py",      title="Board Library",     icon="🪵")

pg = st.navigation(
    {
        "Projects": [projects_page, quotes_page, detail_page],
        "Tools":    [calc_page, slides_page, boards_page],
    }
)

pg.run()
