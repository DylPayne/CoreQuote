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

logo_path = os.path.join("src", "components", "branding", "core_logo.png")

if os.path.exists(logo_path):
    if hasattr(st, "logo"):
        st.logo(logo_path, size="small", icon_image=logo_path)
    else:
        st.sidebar.image(logo_path, use_container_width=True)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Montserrat:wght@500;600;700&display=swap');

    html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Lato', sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
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
