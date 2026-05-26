# CoreQuote

CoreQuote is a **Streamlit-based cabinetry quoting and cutlist system** designed for kitchen, built-in, and board-based joinery workflows.

It combines:

- project + quote management,
- unit-by-unit cabinet configuration,
- board/hardware libraries,
- automated carcass and panel calculations,
- and downloadable PDF cut lists.

In short: **you define a project, build a quote from units, and CoreQuote generates production-ready cutting and component schedules.**

---

## What this project does

CoreQuote helps convert design intent into shop-floor output.

### 1) Project and quote management
- Create projects with client, address, and notes.
- Create multiple quotes per project (e.g., revisions/options).
- Store quote-level defaults for materials, dimensions, and hardware.

### 2) Unit-based cabinet configuration
- Add units to a quote (base drawer, base door, wall door, tall units).
- Configure dimensions per unit (H/W/D), board assignments, and thickness.
- Apply hardware (slides, hinges, handles) with override controls.
- Support advanced drawer-front distributions (equal/custom/manual heights).

### 3) Library-driven defaults
- Manage reusable libraries for:
  - **Boards** (brand, material, thickness, sheet size)
  - **Slides** (length, side clearances, uplift)
  - **Hinges** (opening angle)
  - **Handles** (name/supplier/code)
- Use libraries to set sensible defaults at quote level and per-unit level.

### 4) Cutting list generation
- Build carcass and panel schedules from all units in a quote.
- Aggregate boards into tabular cut lists.
- Export cut lists to PDF.

### 5) Component counting
- Automatically compute hardware counts (e.g., slide pairs, hinge totals, handle totals)
  based on unit definitions and dimensions.

---

## Application flow (high level)

1. Open **Projects** → create/select a project.
2. Open **Quotes** → create a quote and set defaults.
3. Open **Quote Detail**:
   - add/edit units,
   - configure panel presets/manual extras,
   - view cutting lists and component counts,
   - download PDF outputs.
4. Use **Tools/Libraries** pages to maintain boards/slides/hinges/handles.

---

## Architecture overview

CoreQuote is split into clear layers:

- **Streamlit app (`apps/streamlit`)**
  - Streamlit multipage app, forms, dialogs, list/edit screens.
  - Reusable library-page engine (`ui/library_engine.py`) for CRUD-style inventory pages.

- **Reusable logic package (`packages/corequote-core/corequote_core`)**
  - Datamodels (`models.py`) for typed entities such as `Board` and `Slide`.
  - Unit model definitions (`units/`) and a **strategy-based cutting engine** (`cutting/`).
  - Cutlist integration (`cutlist.py`) to transform units → DataFrames.
  - PDF generation (`pdf_gen.py`) for downloadable schedules.

- **Persistence layer (`corequote_core/database.py`)**
  - SQLite-backed storage for projects, quotes, units, board types, slides, hinges, handles.
  - Lightweight schema migrations at startup.
  - Legacy CSV-to-DB seeding for slides.

- **Future apps (`apps/api`, `apps/web`)**
  - Reserved for the FastAPI backend and Next.js frontend.

### Cutting engine design

The cutting system uses a **strategy dispatcher**:

- `CuttingEngine` selects a strategy based on unit type.
- Strategy classes contain all dimension formulas.
- Adding a new unit type is mostly additive (new strategy + registration), keeping core engine stable.

This keeps calculation logic modular and easier to extend/test.

---

## Tech stack

- **Python 3.14+**
- **Streamlit** (application UI)
- **SQLite** (local persistence)
- **pandas** (tabular cutlist shaping)
- **fpdf2** (PDF output)

---

## Repository structure

```text
CoreQuote/
├── apps/
│   ├── api/                    # FastAPI backend placeholder
│   ├── streamlit/              # existing Streamlit app
│   │   ├── main.py             # Streamlit app entry + navigation
│   │   ├── pages/              # Projects, Quotes, Quote Detail, Calculator, libraries
│   │   ├── ui/                 # shared Streamlit UI helpers
│   │   └── components/         # Streamlit visual assets
│   └── web/                    # future Next.js frontend placeholder
├── data/
│   ├── corequote.db            # runtime SQLite database
│   └── slides.csv              # legacy slide seed source
├── infra/                      # future Docker/Alembic/deployment config
├── packages/
│   └── corequote-core/
│       └── corequote_core/     # reusable Python logic package
├── tests/
│   └── unit/                   # unit tests for core logic and UI helpers
├── pyproject.toml
└── README.md
```

---

## Getting started

### 1) Clone

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
streamlit run apps/streamlit/main.py
```

Open the URL shown in your terminal (typically `http://localhost:8501`).

---

## Data and persistence notes

- Main runtime database: `data/corequote.db`
- On startup, the app ensures schema/table availability and applies lightweight migrations.
- If `slides` table is empty, data can be imported from `data/slides.csv` once.

---

## Current scope and intent

CoreQuote is currently focused on **local, single-user workflow support** for cabinetry estimation and production prep. The design favors practical shop usage:

- fast data entry,
- repeatable defaults,
- predictable board/hardware outputs,
- and simple local deployment.

---

## Contributing

1. Create a feature branch.
2. Keep changes focused and well-scoped.
3. Add/update tests where applicable.
4. Open a pull request with a clear summary.

---

## License

No license file is currently included. If you want this project to be openly reusable, add a `LICENSE` file (for example MIT) and update this section.
