import streamlit as st
import sys
import os

# Add src to path for absolute imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

st.set_page_config(
    page_title="Core Quotes",
    page_icon=":material/straighten:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Montserrat:wght@500;600;700&display=swap');

    :root {
        --core-logo-letter-spacing: 0.28em;
    }

    html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Lato', sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
    }

    .core-sidebar-logo {
        font-family: 'Montserrat', sans-serif;
        font-weight: 400;
        font-size: 1.15rem;
        letter-spacing: var(--core-logo-letter-spacing);
        text-transform: uppercase;
        line-height: 1;
        margin: 0.25rem 0 0.9rem 0;
    }

    [data-testid="stSidebarNav"]::before {
        content: "CORE";
        display: block;
        font-family: 'Montserrat', sans-serif;
        font-weight: 400;
        font-size: 1.15rem;
        letter-spacing: var(--core-logo-letter-spacing);
        text-transform: uppercase;
        line-height: 1;
        padding: 0.35rem 0.2rem 0.9rem 0.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Navigation ─────────────────────────────────────────────────────────────────

projects_page = st.Page("pages/_Projects.py",    title="Projects",          icon=":material/folder:")
quotes_page   = st.Page("pages/_Quotes.py",      title="Quotes",            icon=":material/request_quote:")
detail_page   = st.Page("pages/_QuoteDetail.py", title="Quote Detail",      icon=":material/description:")
calc_page     = st.Page("pages/_Calculator.py",  title="Cutlist Generator", icon=":material/build:")
slides_page   = st.Page("pages/_Slides.py",      title="Slides Library",    icon=":material/view_list:")
hinges_page   = st.Page("pages/_Hinges.py",      title="Hinges Library",    icon=":material/hardware:")
boards_page   = st.Page("pages/_Boards.py",      title="Board Library",     icon=":material/grid_view:")

pg = st.navigation(
    {
        "Projects": [projects_page, quotes_page, detail_page],
        "Tools":    [calc_page, slides_page, hinges_page, boards_page],
    }
)

pg.run()
