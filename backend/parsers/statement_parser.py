import re
import csv
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
from pypdf import PdfReader
import io

from parsers.vendor_normalizer import vendor_normalizer


class StatementParser:
    """Parse bank and credit card statements from PDF and CSV files"""

    def __init__(self):
        self._ocr_engine = None
        self._ocr_lock = threading.Lock()
        self.date_patterns = [
            r"\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b",
            r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
            r"\b\d{1,2}[ -][A-Za-z]{3,9}(?:[ -]\d{2,4})?\b",
            r"\b[A-Za-z]{3,9}[ -]\d{1,2}(?:,?[ -]\d{2,4})?\b",
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
        text = self._decode_statement_text(content)
        delimiter, header_index = self._discover_csv_layout(text)
        if header_index is None:
            return self._parse_generic_csv(content, account_type)

        try:
            df = pd.read_csv(
                io.StringIO(text),
                sep=delimiter,
                header=header_index,
                dtype=str,
                keep_default_na=False,
                engine="python",
            )
        except (ValueError, pd.errors.ParserError) as exc:
            raise ValueError("Unable to read CSV statement") from exc

        columns = self._map_csv_columns(list(df.columns))
        date_col = columns.get("date")
        desc_col = columns.get("description")
        amount_col = columns.get("amount")
        debit_col = columns.get("debit")
        credit_col = columns.get("credit")
        if not date_col or not desc_col or not (amount_col or debit_col or credit_col):
            return self._parse_generic_csv(content, account_type)

        currency_col = columns.get("currency")
        type_col = columns.get("type")
        detected_currency = self._detect_currency_from_statement(
            text, df, amount_col or debit_col or credit_col, currency_col
        )
        day_first = self._infer_day_first(df[date_col].tolist())
        if day_first is None:
            raw_date_header = str(date_col).lower()
            if re.search(r"d{1,2}\s*[/.-]\s*m{1,2}", raw_date_header):
                day_first = True
            elif re.search(r"m{1,2}\s*[/.-]\s*d{1,2}", raw_date_header):
                day_first = False
            elif detected_currency in {
                "INR",
                "EUR",
                "GBP",
                "AUD",
                "NZD",
                "ZAR",
                "SGD",
                "HKD",
            }:
                day_first = True
        card_positive_is_debit = (
            self._infer_card_sign_convention(df, amount_col, desc_col, type_col)
            if account_type == "credit_card" and amount_col
            else True
        )
        transactions = []
        rejected_rows = []

        for row_index, row in df.iterrows():
            try:
                description = self._clean_cell(row.get(desc_col))
                if not description or description.lower() in {"nan", "none", "null"}:
                    continue
                date = self._parse_date_value(row.get(date_col), day_first)
                amount_str, explicit_type = self._select_csv_amount(
                    row, amount_col, debit_col, credit_col, type_col
                )
                amount = self._extract_amount(amount_str)
                if explicit_type is None and account_type == "credit_card":
                    explicit_type = (
                        "debit" if (amount >= 0) == card_positive_is_debit else "credit"
                    )
                currency = (
                    self._extract_currency(
                        amount_str, row.get(currency_col) if currency_col else None
                    )
                    or detected_currency
                )
                transaction = self._build_transaction(
                    date,
                    amount,
                    currency,
                    description,
                    account_type,
                    explicit_type,
                )
                if transaction:
                    transactions.append(transaction)
            except (ValueError, TypeError, OverflowError) as exc:
                # Do not silently import a partial statement. Footer rows normally
                # have no transaction date; dated rows are expected transactions.
                if self._clean_cell(row.get(date_col)):
                    rejected_rows.append((int(row_index) + header_index + 2, str(exc)))
        if rejected_rows:
            rows = ", ".join(str(row) for row, _ in rejected_rows[:10])
            raise ValueError(f"Could not safely parse transaction row(s): {rows}")
        return transactions

    def _parse_generic_csv(self, content: bytes, account_type: str) -> List[Dict]:
        """Fallback for headerless date/amount/description CSV exports."""
        text = self._decode_statement_text(content)
        delimiter, _ = self._discover_csv_layout(text)
        lines = text.splitlines()
        transactions = []
        detected_currency = self._extract_currency(text) or "USD"
        rows = list(csv.reader(lines, delimiter=delimiter))
        if rows and not self._looks_like_date(rows[0][0] if rows[0] else ""):
            rows = rows[1:]
        day_first = self._infer_day_first([row[0] for row in rows if row])
        rejected_rows = []

        for row_number, parts in enumerate(rows, start=1):
            parts = [p.strip() for p in parts]
            if len(parts) >= 3:
                try:
                    date = self._parse_date_value(parts[0], day_first)
                    amount_str = parts[1]
                    currency = self._extract_currency(amount_str) or detected_currency
                    amount = self._extract_amount(amount_str)
                    description = ",".join(parts[2:])
                    transaction = self._build_transaction(
                        date, amount, currency, description, account_type
                    )
                    if transaction:
                        transactions.append(transaction)
                except (ValueError, TypeError, OverflowError):
                    if self._looks_like_date(parts[0]):
                        rejected_rows.append(row_number)

        if rejected_rows:
            rows_text = ", ".join(str(row) for row in rejected_rows[:10])
            raise ValueError(f"Could not safely parse transaction row(s): {rows_text}")

        return transactions

    @staticmethod
    def _decode_statement_text(content: bytes) -> str:
        """Decode the encodings most commonly emitted by banking portals."""
        for encoding in ("utf-8-sig", "utf-16", "cp1252"):
            try:
                text = content.decode(encoding)
                if "\x00" not in text:
                    return text
            except UnicodeError:
                continue
        raise ValueError("Unsupported statement text encoding")

    def _discover_csv_layout(self, text: str) -> Tuple[str, Optional[int]]:
        sample = "\n".join(text.splitlines()[:40])
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","

        header_index = None
        best_score = 0
        for index, row in enumerate(
            csv.reader(text.splitlines()[:40], delimiter=delimiter)
        ):
            roles = {self._csv_column_role(value) for value in row}
            score = sum(role in roles for role in ("date", "description"))
            score += 1 if roles.intersection({"amount", "debit", "credit"}) else 0
            if score > best_score:
                best_score = score
                header_index = index
        return delimiter, header_index if best_score >= 3 else None

    @staticmethod
    def _normalize_header(value: str) -> str:
        value = str(value).replace("\ufeff", "").lower()
        value = re.sub(r"\([^)]*\)", " ", value)
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    def _csv_column_role(self, column: str) -> Optional[str]:
        name = self._normalize_header(column)
        aliases = {
            "date": {
                "date",
                "transaction date",
                "txn date",
                "posting date",
                "posted date",
                "post date",
                "posted",
                "booked",
                "book date",
                "booking date",
                "value date",
                "effective date",
            },
            "description": {
                "description",
                "transaction description",
                "merchant",
                "merchant name",
                "details",
                "transaction details",
                "narration",
                "particulars",
                "memo",
                "payee",
                "name",
                "reference",
                "remarks",
                "transaction",
                "info",
                "additional information",
                "transaction narrative",
            },
            "amount": {
                "amount",
                "transaction amount",
                "value",
                "amt",
                "transaction value",
                "local amount",
                "foreign amount",
                "billing amount",
                "gross amount",
            },
            "debit": {
                "debit",
                "debit amount",
                "withdrawal",
                "withdrawal amount",
                "withdrawals",
                "paid out",
                "money out",
                "outflow",
                "charge amount",
            },
            "credit": {
                "credit",
                "credit amount",
                "deposit",
                "deposit amount",
                "deposits",
                "paid in",
                "money in",
                "inflow",
                "payment amount",
            },
            "currency": {"currency", "currency code", "ccy", "curr"},
            "type": {
                "type",
                "transaction type",
                "debit credit",
                "dr cr",
                "credit debit",
                "indicator",
                "transaction indicator",
            },
        }
        for role, names in aliases.items():
            if name in names:
                return role
        if name.endswith(" date"):
            return "date"
        if "description" in name or "merchant" in name:
            return "description"
        if name.startswith("amount ") or name.endswith(" amount"):
            return "amount"
        return None

    def _map_csv_columns(self, columns: List[str]) -> Dict[str, str]:
        mapped: Dict[str, str] = {}
        date_candidates = []
        for column in columns:
            role = self._csv_column_role(column)
            if role == "date":
                normalized = self._normalize_header(column)
                priority = (
                    0 if normalized in {"transaction date", "date", "txn date"} else 1
                )
                date_candidates.append((priority, column))
            elif role and role not in mapped:
                mapped[role] = column
        if date_candidates:
            mapped["date"] = min(date_candidates, key=lambda item: item[0])[1]
        return mapped

    @staticmethod
    def _clean_cell(value) -> str:
        return "" if value is None else str(value).replace("\u00a0", " ").strip()

    def _select_csv_amount(
        self, row, amount_col, debit_col, credit_col, type_col
    ) -> Tuple[str, Optional[str]]:
        if amount_col:
            value = self._clean_cell(row.get(amount_col))
            if not value:
                raise ValueError("Missing transaction amount")
            explicit_type = (
                self._type_from_indicator(row.get(type_col)) if type_col else None
            )
            return value, explicit_type

        debit = self._clean_cell(row.get(debit_col)) if debit_col else ""
        credit = self._clean_cell(row.get(credit_col)) if credit_col else ""
        if self._is_usable_amount(debit):
            return debit, "debit"
        if self._is_usable_amount(credit):
            return credit, "credit"
        raise ValueError("Missing transaction amount")

    def _is_usable_amount(self, value: str) -> bool:
        if not value or value.lower() in {"-", "--", "n/a", "na", "nil", "null"}:
            return False
        try:
            return self._extract_amount(value) != 0
        except ValueError:
            return False

    def _infer_card_sign_convention(self, df, amount_col, desc_col, type_col) -> bool:
        """Return whether positive amounts represent card purchases/debits."""
        for _, row in df.iterrows():
            value = self._clean_cell(row.get(amount_col))
            if not value:
                continue
            try:
                amount = self._extract_amount(value)
            except ValueError:
                continue
            indicated = (
                self._type_from_indicator(row.get(type_col)) if type_col else None
            )
            if indicated:
                return (amount >= 0) == (indicated == "debit")
            description = self._clean_cell(row.get(desc_col)).lower()
            credit_side_phrases = (
                "payment thank you",
                "payment received",
                "online payment",
                "automatic payment",
                "autopay payment",
                "credit card payment",
                "card payment",
                "refund",
                "cashback",
                "reversal",
                "chargeback",
            )
            if any(phrase in description for phrase in credit_side_phrases):
                # Payments/refunds are credit-side card activity.
                return amount < 0
        return True

    @staticmethod
    def _type_from_indicator(value) -> Optional[str]:
        indicator = re.sub(r"[^a-z]", "", str(value or "").lower())
        if indicator in {"d", "dr", "debit", "withdrawal", "out"}:
            return "debit"
        if indicator in {"c", "cr", "credit", "deposit", "in"}:
            return "credit"
        return None

    def _build_transaction(
        self,
        date: datetime,
        amount: float,
        currency: str,
        description: str,
        account_type: str,
        explicit_type: Optional[str] = None,
    ) -> Optional[Dict]:
        detected_type = vendor_normalizer.detect_transaction_type(
            description, amount, account_type
        )
        transaction_type = (
            detected_type
            if detected_type in {"refund", "transfer", "balance", "ignore"}
            else explicit_type or detected_type
        )
        if transaction_type in {"balance", "ignore"}:
            return None
        subtype = vendor_normalizer.get_transaction_subtype(description)
        category = self._categorize_transaction(description, subtype)
        if transaction_type == "transfer":
            category = "Transfers"
        elif transaction_type == "refund":
            category = "Refunds"
        return {
            "date": date,
            "amount": amount,
            "original_amount": amount,
            "currency": currency,
            "description": description.strip(),
            "vendor": vendor_normalizer.extract_vendor(description),
            "transaction_type": transaction_type,
            "subtype": subtype,
            "category": category,
        }

    @staticmethod
    def _looks_like_date(value: str) -> bool:
        return bool(
            re.search(
                r"(?:\d{1,4}[./-]){2}\d{1,4}|\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{2,4})?",
                str(value),
            )
        )

    @staticmethod
    def _infer_day_first(values: List[str]) -> Optional[bool]:
        for value in values:
            match = re.search(
                r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-]\d{2,4}(?!\d)",
                str(value),
            )
            if not match:
                continue
            first, second = map(int, match.groups())
            if first > 12 >= second:
                return True
            if second > 12 >= first:
                return False
        return None

    def _parse_date_value(self, value, day_first: Optional[bool] = None) -> datetime:
        text = self._clean_cell(value)
        if not text:
            raise ValueError("Missing transaction date")
        # ISO and named-month formats are not locale ambiguous.
        for fmt in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%d %b %Y",
            "%d %B %Y",
            "%d %b %y",
            "%d %B %y",
            "%b %d %Y",
            "%B %d %Y",
            "%b %d %y",
            "%B %d %y",
            "%d-%b-%Y",
            "%d-%b-%y",
            "%d/%b/%Y",
            "%d/%b/%y",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        if day_first is None:
            day_first = False
        parsed = pd.to_datetime(text, dayfirst=day_first, errors="raise")
        return parsed.to_pydatetime()

    def _detect_currency_from_statement(
        self, text: str, df, amount_col, currency_col
    ) -> str:
        detected = self._detect_currency_from_data(df, amount_col, currency_col)
        if detected != "USD" or re.search(r"(?<![A-Z])USD(?![A-Z])|\$", text, re.I):
            return detected
        return self._extract_currency(text) or detected

    def _parse_pdf(self, content: bytes, account_type: str) -> List[Dict]:
        """Parse PDF statement"""
        try:
            reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
            if text.strip():
                return self._extract_transactions_from_text(text, account_type)
            return self._extract_transactions_with_ocr(content, account_type)
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError("Unable to extract text from PDF statement") from exc

    def _extract_transactions_with_ocr(
        self, content: bytes, account_type: str
    ) -> List[Dict]:
        """OCR image-only PDFs and preserve table coordinates for safe parsing."""
        try:
            import numpy as np
            import pypdfium2 as pdfium
            from rapidocr import RapidOCR
        except ImportError as exc:
            raise ValueError(
                "This PDF contains no searchable text and OCR support is unavailable"
            ) from exc

        document = pdfium.PdfDocument(content)
        if len(document) > 30:
            raise ValueError("Image-only PDF statements are limited to 30 pages")

        pages = []
        with self._ocr_lock:
            if self._ocr_engine is None:
                self._ocr_engine = RapidOCR()
            for page_number in range(len(document)):
                page = document[page_number]
                bitmap = page.render(scale=120 / 72)
                image = np.asarray(bitmap.to_pil().convert("RGB"))
                result = self._ocr_engine(image)
                lines = []
                if result is None:
                    ocr_items = []
                else:
                    ocr_items = zip(result.boxes, result.txts, result.scores)
                for box, text, confidence in ocr_items:
                    if confidence < 0.55 or not str(text).strip():
                        continue
                    lines.append(
                        {
                            "x0": min(point[0] for point in box),
                            "y0": min(point[1] for point in box),
                            "x1": max(point[0] for point in box),
                            "y1": max(point[1] for point in box),
                            "text": str(text).strip(),
                            "confidence": float(confidence),
                        }
                    )
                pages.append(lines)
                page.close()
        document.close()
        return self._extract_transactions_from_ocr_pages(pages, account_type)

    def _extract_transactions_from_ocr_pages(
        self, pages: List[List[Dict]], account_type: str
    ) -> List[Dict]:
        """Parse deposit/withdrawal/balance tables from positioned OCR text."""
        transactions = []
        current_date = None
        current_balance = None
        pending_details: List[str] = []
        currency = (
            self._extract_currency(
                " ".join(item["text"] for page in pages for item in page)
            )
            or "USD"
        )
        deposit_total = 0.0
        withdrawal_total = 0.0
        reported_totals = None

        for lines in pages:
            header = self._ocr_table_header(lines)
            if not header:
                continue
            header_y, date_x, details_x, deposit_x, withdrawal_x, balance_x = header
            table_lines = [item for item in lines if item["y0"] > header_y + 8]
            clusters = self._cluster_ocr_rows(table_lines)
            deposit_boundary = (deposit_x + withdrawal_x) / 2
            withdrawal_boundary = (withdrawal_x + balance_x) / 2
            amount_start = deposit_x - 85
            details_start = (date_x + details_x) / 2

            for cluster in clusters:
                normalized_text = " ".join(
                    self._normalize_ocr_text(item["text"]) for item in cluster
                )
                if "transactionturnover" in normalized_text:
                    amounts = self._ocr_cluster_amounts(
                        cluster,
                        amount_start,
                        deposit_boundary,
                        withdrawal_boundary,
                    )
                    if amounts.get("deposit") and amounts.get("withdrawal"):
                        reported_totals = (
                            amounts["deposit"],
                            amounts["withdrawal"],
                        )
                    continue
                if "transactioncount" in normalized_text:
                    continue
                if "closingbalance" in normalized_text:
                    pending_details = []
                    continue

                for item in cluster:
                    parsed_date = self._parse_ocr_date(item["text"])
                    if parsed_date:
                        current_date = parsed_date
                        break

                details = [
                    item["text"]
                    for item in cluster
                    if item["x0"] >= details_start
                    and item["x0"] < amount_start
                    and not self._parse_ocr_date(item["text"])
                ]
                pending_details.extend(details)
                amounts = self._ocr_cluster_amounts(
                    cluster,
                    amount_start,
                    deposit_boundary,
                    withdrawal_boundary,
                )
                transaction_amount = amounts.get("deposit") or amounts.get("withdrawal")
                balance = amounts.get("balance")

                if not transaction_amount:
                    if balance is not None and (
                        "balancebroughtforward" in normalized_text
                        or "balancecarriedforward" in normalized_text
                    ):
                        current_balance = balance
                        pending_details = []
                    continue
                if current_date is None:
                    raise ValueError(
                        "OCR transaction found before its transaction date"
                    )
                if balance is None:
                    raise ValueError(
                        f"OCR could not verify the balance for {current_date.date()}"
                    )

                explicit_type = "credit" if amounts.get("deposit") else "debit"
                signed_amount = (
                    abs(transaction_amount)
                    if explicit_type == "credit"
                    else -abs(transaction_amount)
                )
                if account_type == "credit_card":
                    signed_amount = -signed_amount
                if current_balance is not None:
                    expected_balance = current_balance + signed_amount
                    if abs(expected_balance - balance) > 0.02:
                        raise ValueError(
                            "OCR balance validation failed; refusing a partial or "
                            f"incorrect import near {current_date.date()}"
                        )

                description = self._clean_ocr_transaction_description(pending_details)
                if not description:
                    raise ValueError(
                        f"OCR could not read a description for {current_date.date()}"
                    )
                transaction = self._build_transaction(
                    current_date,
                    signed_amount,
                    currency,
                    description,
                    account_type,
                    explicit_type,
                )
                if transaction:
                    transactions.append(transaction)
                current_balance = balance
                if explicit_type == "credit":
                    deposit_total += transaction_amount
                else:
                    withdrawal_total += transaction_amount
                pending_details = []

        if reported_totals and (
            abs(deposit_total - reported_totals[0]) > 0.02
            or abs(withdrawal_total - reported_totals[1]) > 0.02
        ):
            raise ValueError(
                "OCR transaction totals do not match the statement; refusing import"
            )
        return transactions

    def _ocr_table_header(self, lines: List[Dict]):
        candidates = {}
        for item in lines:
            normalized = self._normalize_ocr_text(item["text"])
            role = None
            if normalized == "date":
                role = "date"
            elif normalized.startswith("transactiondetail"):
                role = "details"
            elif normalized.startswith("deposit"):
                role = "deposit"
            elif normalized.startswith("withdraw"):
                role = "withdrawal"
            elif normalized == "balance":
                role = "balance"
            if role:
                candidates.setdefault(role, []).append(item)
        required = {"date", "details", "deposit", "withdrawal", "balance"}
        if not required.issubset(candidates):
            return None
        for date_item in candidates["date"]:
            selected = {"date": date_item}
            for role in required - {"date"}:
                nearby = min(
                    candidates[role],
                    key=lambda item: abs(item["y0"] - date_item["y0"]),
                )
                if abs(nearby["y0"] - date_item["y0"]) > 30:
                    break
                selected[role] = nearby
            if required.issubset(selected):

                def center(item):
                    return (item["x0"] + item["x1"]) / 2

                return (
                    max(item["y1"] for item in selected.values()),
                    center(selected["date"]),
                    center(selected["details"]),
                    center(selected["deposit"]),
                    center(selected["withdrawal"]),
                    center(selected["balance"]),
                )
        return None

    @staticmethod
    def _cluster_ocr_rows(lines: List[Dict]) -> List[List[Dict]]:
        clusters: List[List[Dict]] = []
        for item in sorted(lines, key=lambda value: (value["y0"], value["x0"])):
            if (
                not clusters
                or item["y0"] - min(member["y0"] for member in clusters[-1]) > 6
            ):
                clusters.append([item])
            else:
                clusters[-1].append(item)
        return [sorted(cluster, key=lambda value: value["x0"]) for cluster in clusters]

    def _ocr_cluster_amounts(
        self,
        cluster: List[Dict],
        amount_start: float,
        deposit_boundary: float,
        withdrawal_boundary: float,
    ) -> Dict[str, float]:
        amounts = {}
        for item in cluster:
            center = (item["x0"] + item["x1"]) / 2
            if center < amount_start:
                continue
            try:
                amount = self._extract_amount(item["text"])
            except ValueError:
                continue
            if center < deposit_boundary:
                role = "deposit"
            elif center < withdrawal_boundary:
                role = "withdrawal"
            else:
                role = "balance"
            amounts[role] = amount
        return amounts

    def _parse_ocr_date(self, value: str) -> Optional[datetime]:
        compact = re.sub(r"[^A-Za-z0-9]", "", value)
        if not re.fullmatch(r"\d{1,2}[A-Za-z]{3,9}\d{2,4}", compact):
            return None
        for fmt in ("%d%b%Y", "%d%B%Y", "%d%b%y", "%d%B%y"):
            try:
                return datetime.strptime(compact, fmt)
            except ValueError:
                pass
        return None

    @staticmethod
    def _normalize_ocr_text(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _clean_ocr_transaction_description(self, values: List[str]) -> str:
        descriptions = []
        ignored = {
            "balancebroughtforward",
            "balancecarriedforward",
            "closingbalance",
        }
        for value in values:
            cleaned = re.sub(r"\s+", " ", value).strip(" -|:,")
            normalized = self._normalize_ocr_text(cleaned)
            if (
                not cleaned
                or normalized in ignored
                or not re.search(r"[A-Za-z]", cleaned)
            ):
                continue
            if re.fullmatch(r"\d{6,}", normalized):
                continue
            if re.match(
                r"^(?:upi|hsbcn|axispo|axodh|utibn|idfb|barb|hdfc)\w*\d",
                normalized,
            ):
                continue
            descriptions.append(cleaned)
        return " | ".join(descriptions)

    def _extract_transactions_from_text(
        self, text: str, account_type: str
    ) -> List[Dict]:
        """Extract transactions from PDF text"""
        transactions = []
        lines = text.split("\n")
        statement_year = self._statement_year(text)
        day_first = self._infer_day_first(lines)
        current_date = None
        pending_description = ""
        pending_line = -10

        for i, line in enumerate(lines):
            date_match = None
            for pattern in self.date_patterns:
                candidate = re.search(pattern, line)
                if not candidate:
                    continue
                try:
                    current_date = self._parse_pdf_date(
                        candidate.group(), statement_year, day_first
                    )
                    date_match = candidate
                    break
                except ValueError:
                    pass

            without_date = line
            if date_match:
                without_date = line[: date_match.start()] + line[date_match.end() :]
            amount_matches = self._find_pdf_amounts(without_date)

            if current_date and not amount_matches and date_match:
                pending_description = self._clean_pdf_description(without_date, [])
                pending_line = i
                continue
            if not current_date or not amount_matches:
                continue

            # Running balances are conventionally the last monetary column. The
            # first marked/signed monetary value is the transaction value; when
            # no markers exist, prefer the first value rather than the balance.
            amount_match = next(
                (
                    match
                    for match in amount_matches
                    if re.search(r"\b(?:CR|DR)\b", match.group(0), re.I)
                ),
                amount_matches[0],
            )
            description = self._clean_pdf_description(without_date, amount_matches)
            if (not description or len(description) < 3) and i - pending_line <= 2:
                description = pending_description
            pending_description = ""
            if not description or len(description) < 3:
                continue

            try:
                token = amount_match.group(0).strip()
                amount = self._extract_amount(token)
                marker = re.search(r"\b(CR|DR)\b", token, re.I)
                explicit_type = None
                if marker:
                    explicit_type = (
                        "credit" if marker.group(1).upper() == "CR" else "debit"
                    )
                    if account_type == "credit_card":
                        amount = (
                            -abs(amount) if explicit_type == "credit" else abs(amount)
                        )
                    else:
                        amount = (
                            abs(amount) if explicit_type == "credit" else -abs(amount)
                        )
                transaction = self._build_transaction(
                    current_date,
                    amount,
                    self._extract_currency(line)
                    or self._extract_currency(text)
                    or "USD",
                    description,
                    account_type,
                    explicit_type,
                )
                if transaction:
                    transactions.append(transaction)
            except (ValueError, TypeError, OverflowError):
                continue

        return transactions

    def _find_pdf_amounts(self, line: str):
        currency = r"(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|MXN|BRL|ZAR|SGD|HKD|NZD|C\$|A\$|S\$|HK\$|NZ\$|R\$|[$€£¥₹])"
        pattern = re.compile(
            rf"(?<![\w/])\(?[-+]?\s*(?:{currency}\s*)?\d[\d ,'’]*(?:[.,]\d{{1,3}})?\s*(?:CR|DR)?\)?(?![\w/])",
            re.I,
        )
        matches = []
        for match in pattern.finditer(line):
            token = match.group(0).strip()
            # Plain integers are commonly reference/account numbers. Accept them
            # only when a currency or direction marker makes them monetary.
            if not re.search(r"[.,]|CR|DR|[$€£¥₹]", token, re.I) and not re.search(
                r"\b(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|MXN|BRL|ZAR|SGD|HKD|NZD)\b",
                token,
                re.I,
            ):
                continue
            matches.append(match)
        return matches

    @staticmethod
    def _clean_pdf_description(line: str, amount_matches) -> str:
        description = line
        for match in reversed(amount_matches):
            description = (
                description[: match.start()] + " " + description[match.end() :]
            )
        description = re.sub(r"\b(?:CR|DR)\b", " ", description, flags=re.I)
        return re.sub(r"\s+", " ", description).strip(" -|:,\t")

    @staticmethod
    def _statement_year(text: str) -> Optional[int]:
        years = [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", text)]
        return max(set(years), key=years.count) if years else None

    def _parse_pdf_date(
        self, value: str, statement_year: Optional[int], day_first: Optional[bool]
    ) -> datetime:
        text = value.strip().replace(",", "")
        named_date_has_year = re.fullmatch(
            r"(?:\d{1,2}[ -][A-Za-z]{3,9}|[A-Za-z]{3,9}[ -]\d{1,2})"
            r"[ -]\d{2,4}",
            text,
        )
        if re.search(r"[A-Za-z]", text) and not named_date_has_year:
            if statement_year is None:
                raise ValueError("Yearless PDF date without a statement year")
            text = f"{text} {statement_year}"
        return self._parse_date_value(text, day_first)

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        return self._parse_date_value(date_str)

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
            if re.search(rf"(?<![A-Z]){re.escape(code)}(?![A-Z])", amount_str, re.I):
                return code

        # Check for currency symbols
        for symbol, code in sorted(
            self.currency_symbols.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if symbol in amount_str:
                return code

        return None

    def _extract_amount(self, amount_str: str) -> float:
        """Parse localized/accounting amounts without turning invalid data into zero."""
        cleaned = self._clean_cell(amount_str)
        if not cleaned:
            raise ValueError("Missing transaction amount")
        is_negative = bool(re.search(r"^\s*-|[-−]\s*$|^\s*\(.*\)\s*$", cleaned))
        cleaned = cleaned.replace("−", "-")
        cleaned = re.sub(r"\b(?:CR|DR)\b", "", cleaned, flags=re.I)
        for symbol in sorted(self.currency_symbols, key=len, reverse=True):
            cleaned = cleaned.replace(symbol, "")
        for code in self.currency_codes:
            cleaned = re.sub(
                rf"(?<![A-Za-z]){re.escape(code)}(?![A-Za-z])", "", cleaned, flags=re.I
            )
        cleaned = cleaned.strip().strip("()").strip()
        cleaned = re.sub(r"[-+]\s*$", "", cleaned).strip()
        cleaned = cleaned.lstrip("+").strip()
        if cleaned.startswith("-"):
            cleaned = cleaned[1:].strip()
            is_negative = True
        cleaned = re.sub(r"[\s'’]", "", cleaned)

        if not re.fullmatch(r"\d+(?:[.,]\d+)*(?:[.,]\d+)?", cleaned):
            raise ValueError(f"Invalid transaction amount: {amount_str}")

        if "," in cleaned and "." in cleaned:
            decimal = "," if cleaned.rfind(",") > cleaned.rfind(".") else "."
            thousands = "." if decimal == "," else ","
            cleaned = cleaned.replace(thousands, "").replace(decimal, ".")
        elif "," in cleaned:
            groups = cleaned.split(",")
            if len(groups[-1]) in {1, 2}:
                cleaned = "".join(groups[:-1]) + "." + groups[-1]
            else:
                cleaned = "".join(groups)
        elif cleaned.count(".") > 1:
            groups = cleaned.split(".")
            if len(groups[-1]) in {1, 2}:
                cleaned = "".join(groups[:-1]) + "." + groups[-1]
            else:
                cleaned = "".join(groups)

        try:
            amount = float(cleaned)
        except ValueError as exc:
            raise ValueError(f"Invalid transaction amount: {amount_str}") from exc
        return -amount if is_negative and amount else amount
