# Personal Finance Tracker

A comprehensive personal finance tracking application that analyzes your spending patterns, provides savings recommendations, and generates a psychological financial profile.

## Features

- 📊 **Monthly Expense Tracking**: Track expenses across multiple categories
- 💰 **Savings Recommendations**: Get rule-based suggestions on where to save
- 🧠 **Spending Behavior Profile**: Explore rule-based spending patterns
- 📄 **Statement Parsing**: Automatically parse credit card and bank statements (PDF/CSV)
- 📈 **Trend Analysis**: Visualize spending trends over time
- 👤 **Private Accounts**: Individual signup/login with isolated financial data
- 💾 **Local Storage**: Financial data stays in your configured database
- 🎨 **Beautiful UI**: Modern, animated interface with charts and visualizations

## Tech Stack

- **Frontend**: Next.js 15, React, Tailwind CSS, Framer Motion, Recharts
- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Parsing**: PyPDF2, pandas for statement processing

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./start.sh
```

Then follow the instructions to start both servers in separate terminals.

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend will run on `http://localhost:8000`

For production, configure both services with the same server-side token:

```bash
# FastAPI
ENVIRONMENT=production FINANCE_API_TOKEN='replace-with-a-long-random-value' uvicorn main:app

# Next.js (never prefix these variables with NEXT_PUBLIC_)
ENVIRONMENT=production BACKEND_API_URL='http://localhost:8000' \
FINANCE_API_TOKEN='replace-with-the-same-value' \
npm start
```

The Next.js server proxies browser requests to FastAPI, so the token is not shipped in client JavaScript. You may also set `MAX_UPLOAD_BYTES` and `ALLOWED_ORIGINS` on the backend.

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:3000`

### First Time Usage

1. Open `http://localhost:3000` and create an account
2. Sign in and open the "Upload" tab
3. Upload a CSV or PDF statement file
4. View your private dashboard with categorized expenses
5. Explore insights, trends, and spending patterns

## Features in Detail

### 📊 Dashboard
- Monthly spending overview with visual cards
- Interactive pie charts showing category breakdown
- Bar charts for spending comparison
- Savings recommendations with actionable insights

### 📤 Statement Upload
- Support for PDF and CSV files
- Automatic transaction extraction
- Smart categorization of expenses
- Support for both credit card and bank account statements

### 📈 Categories View
- Detailed breakdown by spending category
- Interactive category selection
- Transaction list filtered by category
- Visual representation with pie charts

### 📉 Trends Analysis
- Monthly spending trends over time
- Comparison across multiple months
- Average, highest, and lowest month statistics
- Visual trend indicators

### 🧠 Spending Patterns
- Neutral, rule-based observations from recent expenses
- Discretionary category share and category concentrations
- Explicit limitations instead of psychological claims

## Sample Data

A sample CSV file (`sample_data.csv`) is included for testing. You can upload it to see how the system works.

## Data Privacy

- Data is stored in the configured SQLite database by default (or PostgreSQL when `DATABASE_URL` is set)
- Every statement, transaction, analysis period, and learned category rule is owned by one account
- Passwords are salted and hashed with scrypt; revocable session tokens are hashed in the database and stored in an HttpOnly, same-site browser cookie
- When upgrading an existing single-user installation, the first account created claims legacy data; later accounts start empty
- Transaction data is not sent to external servers; the backend fetches public exchange rates
- Analyses are calculated from local transactions on demand
- In production, keep FastAPI private and configure the same `FINANCE_API_TOKEN` on FastAPI and Next.js

## Verification

```bash
cd backend && pip install -r requirements-dev.txt && pytest && ruff check .
cd frontend && npm ci && npm test && npm run lint && npm run build && npm audit --omit=dev
```

## Project Structure

```
personal-finance-tracker/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── database.py          # Database setup
│   ├── parsers/             # Statement parsers
│   ├── analytics/           # Analysis engine
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── app/                 # Next.js app directory
│   ├── components/          # React components
│   └── package.json         # Node dependencies
└── README.md
```
