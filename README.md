# Personal Finance Tracker

A comprehensive personal finance tracking application that analyzes your spending patterns, provides savings recommendations, and generates a psychological financial profile.

## Features

- 📊 **Monthly Expense Tracking**: Track expenses across multiple categories
- 💰 **Savings Recommendations**: Get AI-powered suggestions on where to save
- 🧠 **Psychological Financial Profile**: Understand your spending behavior patterns
- 📄 **Statement Parsing**: Automatically parse credit card and bank statements (PDF/CSV)
- 📈 **Trend Analysis**: Visualize spending trends over time
- 💾 **Local Storage**: All data stored locally for privacy
- 🎨 **Beautiful UI**: Modern, animated interface with charts and visualizations

## Tech Stack

- **Frontend**: Next.js 14, React, Tailwind CSS, Framer Motion, Recharts
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

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:3000`

### First Time Usage

1. Open `http://localhost:3000` in your browser
2. Click on the "Upload" tab
3. Upload a CSV or PDF statement file
4. View your dashboard with categorized expenses
5. Explore insights, trends, and your psychological profile

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

### 🧠 Psychological Profile
- Spending personality analysis
- Impulse spending indicators
- Financial habits identification
- Risk factors and strengths assessment
- Personalized insights and recommendations

## Sample Data

A sample CSV file (`sample_data.csv`) is included for testing. You can upload it to see how the system works.

## Data Privacy

- All data is stored locally in SQLite database
- No data is sent to external servers
- Only analysis results are stored for trend tracking
- Your financial data remains completely private

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

