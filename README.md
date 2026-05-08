# CoreQuote

CoreQuote is a **Streamlit-based quoting and cutlist assistant** for cabinetry and board-based projects.
It helps manage projects, quotes, units, slides, and board libraries in one place.

## Features

- Project and quote management
- Unit setup with sizing and parameters
- Cutlist generation tools
- Slides and boards library pages
- Local SQLite persistence (`data/corequote.db`)

## Tech Stack

- Python 3.14+
- Streamlit
- SQLite
- pandas
- fpdf2

## Project Structure

```text
CoreQuote/
├── data/
│   ├── corequote.db
│   └── slides.csv
├── src/
│   ├── main.py
│   ├── logic/
│   └── pages/
├── pyproject.toml
└── README.md
```

## Getting Started

### 1) Clone the repository

```bash
git clone https://github.com/DylPayne/CoreQuote.git
cd CoreQuote
```

### 2) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

Using pip:

```bash
pip install -e .
```

Or with uv:

```bash
uv sync
```

### 4) Run the app

```bash
streamlit run src/main.py
```

Then open the local URL shown in your terminal (usually `http://localhost:8501`).

## Data Notes

- The app stores runtime data in `data/corequote.db`.
- Initial slide data may be sourced from `data/slides.csv`.

## Contributing

1. Create a feature branch
2. Commit your changes with clear messages
3. Open a pull request

## License

If you want, you can add a `LICENSE` file (for example MIT) and update this section accordingly.
