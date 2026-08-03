import re
from datetime import datetime
from typing import List, Dict
import pandas as pd
from pypdf import PdfReader
import io

from parsers.vendor_normalizer import vendor_normalizer


class StatementParser:
    """Parse bank and credit card statements from PDF and CSV files"""

    def __init__(self):
        self.date_patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            r"\d{4}-\d{2}-\d{2}",
            r"\d{1,2}\s+\w{3}\s+\d{4}",
        ]
        # Currency symbols and codes
        self.currency_symbols = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "JPY",
            "C$": "CAD",
            "A$": "AUD",
            "CHF": "CHF",
            "₹": "INR",
            "R$": "BRL",
            "S$": "SGD",
            "HK$": "HKD",
            "NZ$": "NZD",
            "MXN": "MXN",
            "ZAR": "ZAR",
            "CNY": "CNY",
        }
        self.currency_codes = [
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "CAD",
            "AUD",
            "CHF",
            "CNY",
            "INR",
            "MXN",
            "BRL",
            "ZAR",
            "SGD",
            "HKD",
            "NZD",
        ]

    def parse_file(
        self, file_content: bytes, filename: str, account_type: str
    ) -> List[Dict]:
        """Parse a statement file and return list of transactions"""
        extension = filename.lower()
        if extension.endswith(".csv"):
            return self._parse_csv(file_content, account_type)
        elif extension.endswith(".pdf"):
            return self._parse_pdf(file_content, account_type)
        else:
            raise ValueError(f"Unsupported file type: {filename}")

    def _parse_csv(self, content: bytes, account_type: str) -> List[Dict]:
        """Parse CSV statement"""
        try:
            df = pd.read_csv(io.BytesIO(content))
            transactions = []

            # Common CSV column patterns
            date_col = None
            amount_col = None
            debit_col = None
            credit_col = None
            desc_col = None
            currency_col = None

            for col in df.columns:
                col_lower = col.lower()
                if "date" in col_lower and date_col is None:
                    date_col = col
                normalized = re.sub(r"[^a-z]+", " ", col_lower).strip()
                if (
                    normalized in {"amount", "transaction amount", "value"}
                    and amount_col is None
                ):
                    amount_col = col
                if (
                    normalized
                    in {"debit", "debit amount", "withdrawal", "withdrawal amount"}
                    and debit_col is None
                ):
                    debit_col = col
                if (
                    normalized
                    in {"credit", "credit amount", "deposit", "deposit amount"}
                    and credit_col is None
                ):
                    credit_col = col
                if (
                    "description" in col_lower
                    or "merchant" in col_lower
                    or "details" in col_lower
                ) and desc_col is None:
                    desc_col = col
                if "currency" in col_lower and currency_col is None:
                    currency_col = col

            # Detect currency from first row or filename
            detected_currency = self._detect_currency_from_data(
                df, amount_col or debit_col or credit_col, currency_col
            )

            if date_col and (amount_col or debit_col or credit_col) and desc_col:
                for _, row in df.iterrows():
                    try:
                        date = pd.to_datetime(row[date_col]).to_pydatetime()
                        explicit_type = None
                        if amount_col:
                            amount_str = str(row[amount_col])
                        else:
                            debit_value = row.get(debit_col) if debit_col else None
                            credit_value = row.get(credit_col) if credit_col else None
                            if pd.notna(debit_value) and str(
                                debit_value
                            ).strip() not in {"", "0", "0.0"}:
                                amount_str = str(debit_value)
                                explicit_type = "debit"
                            elif pd.notna(credit_value) and str(
                                credit_value
                            ).strip() not in {"", "0", "0.0"}:
                                amount_str = str(credit_value)
                                explicit_type = "credit"
                            else:
                                continue
                        currency = self._extract_currency(
                            amount_str, row.get(currency_col) if currency_col else None
                        )
                        if not currency:
                            currency = detected_currency

                        # Extract numeric amount - preserve sign for debit/credit detection
                        amount = self._extract_amount(amount_str)
                        description = str(row[desc_col]).strip()
                        if description.lower() in {"", "nan", "none"}:
                            raise ValueError("Missing transaction description")

                        # Extract vendor name and detect transaction type
                        vendor = vendor_normalizer.extract_vendor(description)
                        detected_type = vendor_normalizer.detect_transaction_type(
                            description, amount, account_type
                        )
                        transaction_type = (
                            detected_type
                            if detected_type in {"refund", "transfer", "balance", "ignore"}
                            else explicit_type or detected_type
                        )
                        subtype = vendor_normalizer.get_transaction_subtype(description)

                        # Skip balance entries and non-transactions (totals, summaries, etc.)
                        if transaction_type in ("balance", "ignore"):
                            continue

                        transactions.append(
                            {
                                "date": date,
                                "amount": amount,
                                "original_amount": amount,
                                "currency": currency,
                                "description": description,
                                "vendor": vendor,
                                "transaction_type": transaction_type,
                                "subtype": subtype,
                                "category": self._categorize_transaction(
                                    description, subtype
                                ),
                            }
                        )
                    except (ValueError, TypeError, OverflowError):
                        continue

            if (
                not date_col
                or not desc_col
                or not (amount_col or debit_col or credit_col)
            ):
                raise ValueError(
                    "CSV must contain date, description, and amount (or debit/credit) columns"
                )
            return transactions
        except (UnicodeError, ValueError, pd.errors.ParserError):
            # Fallback: try to parse as generic CSV
            return self._parse_generic_csv(content, account_type)

    def _parse_generic_csv(self, content: bytes, account_type: str) -> List[Dict]:
        """Fallback CSV parser"""
        import csv

        lines = content.decode("utf-8-sig").splitlines()
        transactions = []
        detected_currency = "USD"  # Default

        for parts in csv.reader(lines[1:]):
            parts = [p.strip() for p in parts]
            if len(parts) >= 3:
                try:
                    date = datetime.strptime(parts[0], "%Y-%m-%d")
                    amount_str = parts[1]
                    currency = (
                        self._extract_currency(amount_str, None) or detected_currency
                    )
                    amount = self._extract_amount(amount_str)
                    description = ",".join(parts[2:])

                    # Extract vendor and detect transaction type
                    vendor = vendor_normalizer.extract_vendor(description)
                    transaction_type = vendor_normalizer.detect_transaction_type(
                        description, amount, account_type
                    )
                    subtype = vendor_normalizer.get_transaction_subtype(description)

                    # Skip balance entries and non-transactions
                    if transaction_type in ("balance", "ignore"):
                        continue

                    transactions.append(
                        {
                            "date": date,
                            "amount": amount,
                            "original_amount": amount,
                            "currency": currency,
                            "description": description,
                            "vendor": vendor,
                            "transaction_type": transaction_type,
                            "subtype": subtype,
                            "category": self._categorize_transaction(
                                description, subtype
                            ),
                        }
                    )
                except (ValueError, TypeError, OverflowError):
                    continue

        return transactions

    def _parse_pdf(self, content: bytes, account_type: str) -> List[Dict]:
        """Parse PDF statement"""
        try:
            reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"

            return self._extract_transactions_from_text(text, account_type)
        except Exception as exc:
            raise ValueError("Unable to extract text from PDF statement") from exc

    def _extract_transactions_from_text(
        self, text: str, account_type: str
    ) -> List[Dict]:
        """Extract transactions from PDF text"""
        transactions = []
        lines = text.split("\n")

        # Look for transaction patterns
        current_date = None
        for i, line in enumerate(lines):
            # Try to find date
            for pattern in self.date_patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        date_str = match.group()
                        current_date = self._parse_date(date_str)
                        break
                    except ValueError:
                        continue

            # Look for amount patterns
            amount_matches = list(
                re.finditer(
                    r"(?P<paren>\()?[-+]?\s*[\$€£₹]?\s*(?P<value>[\d,]+\.\d{2})\)?\s*(?P<credit>CR|DR)?",
                    line,
                    re.IGNORECASE,
                )
            )
            amount_match = amount_matches[-1] if amount_matches else None
            if amount_match and current_date:
                try:
                    amount = float(amount_match.group("value").replace(",", ""))
                    token = amount_match.group(0)
                    marker = (amount_match.group("credit") or "").upper()
                    if marker == "CR":
                        amount = -amount if account_type == "credit_card" else amount
                    elif marker == "DR":
                        amount = amount if account_type == "credit_card" else -amount
                    elif "(" in token or "-" in token:
                        amount = -amount
                    description = re.sub(r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}", "", line)
                    description = description.replace(amount_match.group(0), "", 1)
                    description = description.strip(" -|") or (
                        lines[i - 1].strip() if i > 0 else ""
                    )
                    transaction_type = vendor_normalizer.detect_transaction_type(
                        description, amount, account_type
                    )
                    if transaction_type in {"balance", "ignore"}:
                        continue

                    if description and len(description) > 3:
                        transactions.append(
                            {
                                "date": current_date,
                                "amount": amount,
                                "original_amount": amount,
                                "currency": self._extract_currency(line) or "USD",
                                "description": description,
                                "transaction_type": transaction_type,
                                "category": self._categorize_transaction(
                                    description,
                                    vendor_normalizer.get_transaction_subtype(
                                        description
                                    ),
                                ),
                            }
                        )
                except (ValueError, TypeError, OverflowError):
                    continue

        return transactions

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%m/%d/%y",
            "%m-%d-%y",
            "%d %b %Y",
            "%d %B %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Unsupported date format: {date_str}")

    def _categorize_transaction(self, description: str, subtype: str = None) -> str:
        """Categorize transaction based on description and subtype"""
        desc_lower = description.lower()

        # Handle subtypes first (more specific)
        if subtype:
            if subtype == "fee":
                return "Fees & Charges"
            elif subtype == "refund":
                return "Refunds"
            elif subtype == "transfer":
                return "Transfers"
            elif subtype == "atm":
                return "Cash Withdrawal"
            elif subtype == "payment":
                return "Bills & Utilities"
            elif subtype == "credit" and any(
                kw in desc_lower for kw in ["salary", "payroll", "deposit"]
            ):
                return "Income"

        # Enhanced category keywords with more patterns
        categories = {
            "Food & Dining": [
                "restaurant",
                "cafe",
                "coffee",
                "food",
                "dining",
                "starbucks",
                "mcdonald",
                "uber eats",
                "doordash",
                "grubhub",
                "swiggy",
                "zomato",
                "pizza",
                "burger",
                "subway",
                "kfc",
                "dominos",
                "dunkin",
                "chipotle",
                "taco bell",
            ],
            "Shopping": [
                "amazon",
                "target",
                "walmart",
                "store",
                "shop",
                "retail",
                "purchase",
                "flipkart",
                "myntra",
                "ebay",
                "ikea",
                "costco",
                "best buy",
                "nordstrom",
            ],
            "Transportation": [
                "uber",
                "lyft",
                "ola",
                "gas",
                "fuel",
                "parking",
                "metro",
                "subway",
                "taxi",
                "petrol",
                "diesel",
                "shell",
                "chevron",
                "bp",
                "exxon",
                "toll",
                "cab",
            ],
            "Bills & Utilities": [
                "electric",
                "water",
                "gas bill",
                "internet",
                "phone",
                "utility",
                "bill",
                "broadband",
                "wifi",
                "mobile",
                "airtel",
                "jio",
                "vodafone",
                "verizon",
                "at&t",
            ],
            "Entertainment": [
                "netflix",
                "spotify",
                "movie",
                "theater",
                "concert",
                "game",
                "entertainment",
                "disney",
                "hbo",
                "prime video",
                "hulu",
                "youtube",
                "gaming",
                "playstation",
                "xbox",
            ],
            "Healthcare": [
                "pharmacy",
                "hospital",
                "doctor",
                "medical",
                "cvs",
                "walgreens",
                "health",
                "dental",
                "clinic",
                "medicine",
                "apollo",
                "lab",
                "diagnostic",
            ],
            "Education": [
                "school",
                "university",
                "tuition",
                "course",
                "education",
                "udemy",
                "coursera",
                "college",
                "academy",
                "book",
                "learning",
            ],
            "Travel": [
                "hotel",
                "flight",
                "airline",
                "travel",
                "booking",
                "airbnb",
                "makemytrip",
                "indigo",
                "spicejet",
                "marriott",
                "hilton",
                "expedia",
                "trivago",
            ],
            "Groceries": [
                "grocery",
                "supermarket",
                "whole foods",
                "trader joe",
                "safeway",
                "kroger",
                "big bazaar",
                "dmart",
                "reliance fresh",
                "organic",
                "vegetables",
                "fruits",
            ],
            "Subscriptions": [
                "subscription",
                "membership",
                "prime",
                "premium",
                "monthly",
                "annual",
            ],
            "Income": [
                "salary",
                "payroll",
                "deposit",
                "income",
                "dividend",
                "interest credit",
                "refund",
                "cashback",
                "bonus",
                "reimbursement",
            ],
            "Transfers": [
                "transfer",
                "neft",
                "imps",
                "upi",
                "rtgs",
                "wire",
                "zelle",
                "venmo",
            ],
        }

        for category, keywords in categories.items():
            if any(
                vendor_normalizer._contains_keyword(desc_lower, keyword)
                for keyword in keywords
            ):
                return category

        return "Other"

    def _detect_currency_from_data(self, df, amount_col, currency_col) -> str:
        """Detect currency from CSV data"""
        if currency_col and currency_col in df.columns:
            # Check first non-null currency value
            for val in df[currency_col].dropna():
                val_str = str(val).upper().strip()
                if val_str in self.currency_codes:
                    return val_str

        # Try to detect from amount column
        if amount_col and amount_col in df.columns:
            for val in df[amount_col].head(10):
                currency = self._extract_currency(str(val), None)
                if currency:
                    return currency

        return "USD"  # Default

    def _extract_currency(self, amount_str: str, currency_code: str = None) -> str:
        """Extract currency from amount string or currency code"""
        if currency_code:
            code = str(currency_code).upper().strip()
            if code in self.currency_codes:
                return code

        amount_str = str(amount_str).strip()

        # Check for currency codes in the string
        for code in self.currency_codes:
            if code in amount_str.upper():
                return code

        # Check for currency symbols
        for symbol, code in sorted(
            self.currency_symbols.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if symbol in amount_str:
                return code

        return None

    def _extract_amount(self, amount_str: str) -> float:
        """Extract numeric amount from string, removing currency symbols but preserving sign"""
        # Remove common currency symbols and codes
        cleaned = str(amount_str).strip()
        for symbol in self.currency_symbols.keys():
            cleaned = cleaned.replace(symbol, "")
        for code in self.currency_codes:
            cleaned = cleaned.replace(code, "").replace(code.lower(), "")

        # Remove commas and extract number (preserve negative sign)
        cleaned = cleaned.replace(",", "").strip()
        # Extract number with optional decimal and negative sign
        # Look for negative sign at the start or parentheses (accounting notation)
        is_negative = (
            cleaned.startswith("-") or cleaned.startswith("(") or cleaned.endswith(")")
        )
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = cleaned.replace("(", "").replace(")", "")
            is_negative = True

        # Extract number with optional decimal
        match = re.search(r"([-]?\d+\.?\d*)", cleaned)
        if match:
            amount = float(match.group(1))
            # Apply negative if detected from parentheses
            if is_negative and amount > 0:
                amount = -amount
            return amount
        return 0.0
