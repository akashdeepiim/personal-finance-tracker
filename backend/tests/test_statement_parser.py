import pytest

from parsers.statement_parser import StatementParser
from parsers.vendor_normalizer import vendor_normalizer


def test_transaction_date_is_not_used_as_amount():
    content = b"Transaction Date,Description,Amount\n2024-01-02,Coffee Shop,-12.50\n"
    transaction = StatementParser().parse_file(
        content, "statement.CSV", "bank_account"
    )[0]
    assert transaction["amount"] == -12.5
    assert transaction["category"] == "Food & Dining"


def test_separate_debit_and_credit_columns_are_supported():
    content = (
        b"Date,Description,Debit,Credit\n"
        b"2024-01-02,Coffee Shop,12.50,\n"
        b"2024-01-03,Salary,,1000.00\n"
    )
    transactions = StatementParser().parse_file(content, "bank.csv", "bank_account")
    assert [item["transaction_type"] for item in transactions] == ["debit", "credit"]


def test_placeholder_in_debit_column_does_not_hide_credit():
    content = (
        b"Date,Description,Debit,Credit\n"
        b"2024-01-02,Salary,-,1000.00\n"
        b"2024-01-03,Refund,N/A,25.00\n"
    )
    transactions = StatementParser().parse_file(content, "bank.csv", "bank_account")
    assert [item["amount"] for item in transactions] == [1000.0, 25.0]
    assert [item["transaction_type"] for item in transactions] == ["credit", "refund"]


def test_card_payment_and_refund_are_not_parsed_as_income():
    bank_content = (
        b"Date,Description,Debit,Credit\n2024-01-02,Credit Card Payment,100.00,\n"
    )
    card_content = (
        b"Date,Description,Amount\n"
        b"2024-01-03,Payment Thank You,-100.00\n"
        b"2024-01-04,Merchant Refund,-25.00\n"
    )
    bank = StatementParser().parse_file(bank_content, "bank.csv", "bank_account")
    card = StatementParser().parse_file(card_content, "card.csv", "credit_card")
    assert bank[0]["transaction_type"] == "transfer"
    assert card[0]["transaction_type"] == "transfer"
    assert card[1]["transaction_type"] == "refund"


def test_credit_card_sign_convention_is_inferred_from_payment_rows():
    content = (
        b"Date,Description,Amount\n"
        b"2024-01-02,Payment Thank You,100.00\n"
        b"2024-01-03,Coffee Shop,-12.50\n"
    )
    transactions = StatementParser().parse_file(content, "card.csv", "credit_card")
    assert [item["transaction_type"] for item in transactions] == ["transfer", "debit"]


def test_generic_payment_merchant_is_not_treated_as_card_transfer():
    transaction_type = vendor_normalizer.detect_transaction_type(
        "Insurance payment", 50.0, "credit_card"
    )
    assert transaction_type == "debit"


def test_keyword_matching_uses_whole_words():
    assert vendor_normalizer.get_transaction_subtype("Coffee Shop") is None
    assert (
        vendor_normalizer.detect_transaction_type(
            "Direct Deposit Salary", 1000, "bank_account"
        )
        == "credit"
    )


def test_pdf_text_preserves_debit_and_credit_semantics():
    parser = StatementParser()
    bank = parser._extract_transactions_from_text(
        "2024-01-02 Coffee Shop -12.50", "bank_account"
    )
    card = parser._extract_transactions_from_text(
        "2024-01-03 Merchant Refund 12.50 CR", "credit_card"
    )
    assert bank[0]["transaction_type"] == "debit"
    assert bank[0]["original_amount"] == -12.5
    assert card[0]["transaction_type"] == "refund"
    assert card[0]["original_amount"] == -12.5


def test_common_csv_encodings_delimiters_preambles_and_headers():
    parser = StatementParser()
    statements = [
        b"Date;Narration;Paid Out\n2024-01-02;Coffee Shop;12.50\n",
        b"Account,1234\nPosted,Memo,Amount\n2024-01-02,Coffee Shop,-12.50\n",
        "Date\tPayee\tAmt\n2024-01-02\tCoffee Shop\t-12.50\n".encode("utf-16"),
        b"Booking Date|Particulars|Withdrawal Amount\n2024-01-02|Coffee Shop|12.50\n",
    ]
    for content in statements:
        transactions = parser.parse_file(content, "statement.csv", "bank_account")
        assert len(transactions) == 1
        assert transactions[0]["description"] == "Coffee Shop"
        assert abs(transactions[0]["amount"]) == 12.5
        assert transactions[0]["transaction_type"] == "debit"


def test_amount_parser_handles_locales_and_rejects_invalid_values():
    parser = StatementParser()
    assert parser._extract_amount("1,234.56-") == -1234.56
    assert parser._extract_amount("(₹1,23,456.78)") == -123456.78
    assert parser._extract_amount("1.234,56 EUR") == 1234.56

    content = b"Date,Description,Amount\n2024-01-02,Invalid,N/A\n"
    with pytest.raises(ValueError, match="Could not safely parse transaction row"):
        parser.parse_file(content, "statement.csv", "bank_account")


def test_type_indicator_and_statement_date_order_are_applied_consistently():
    content = (
        b"Date (DD/MM/YYYY),Description,Amount (INR),DR/CR\n"
        b"02/01/2024,Salary,1000.00,CR\n"
        b"03/01/2024,Coffee Shop,12.50,DR\n"
    )
    transactions = StatementParser().parse_file(
        content, "statement.csv", "bank_account"
    )
    assert [item["date"].day for item in transactions] == [2, 3]
    assert [item["transaction_type"] for item in transactions] == ["credit", "debit"]
    assert {item["currency"] for item in transactions} == {"INR"}


def test_transfer_keywords_are_neutral_transactions():
    parser = StatementParser()
    content = (
        b"Date,Description,Amount\n"
        b"2024-01-02,NEFT TO SAVINGS,-100.00\n"
        b"2024-01-03,UPI TRANSFER TO JOHN,-20.00\n"
    )
    transactions = parser.parse_file(content, "statement.csv", "bank_account")
    assert [item["transaction_type"] for item in transactions] == [
        "transfer",
        "transfer",
    ]
    assert {item["category"] for item in transactions} == {"Transfers"}


def test_pdf_uses_transaction_amount_not_running_balance_and_skips_totals():
    text = "2024-01-02 Coffee Shop 12.50 DR 987.50\nTotal purchases 12.50\n"
    transactions = StatementParser()._extract_transactions_from_text(
        text, "bank_account"
    )
    assert len(transactions) == 1
    assert transactions[0]["amount"] == -12.5
    assert transactions[0]["description"] == "Coffee Shop"


def test_pdf_supports_yearless_multiline_and_zero_decimal_currency_rows():
    text = (
        "Statement Period 01 Jan 2024 to 31 Jan 2024\n"
        "02 Jan Grocery Store\n"
        "JPY 1200 DR\n"
    )
    transactions = StatementParser()._extract_transactions_from_text(
        text, "bank_account"
    )
    assert len(transactions) == 1
    assert transactions[0]["date"].date().isoformat() == "2024-01-02"
    assert transactions[0]["amount"] == -1200
    assert transactions[0]["currency"] == "JPY"
    assert transactions[0]["description"] == "Grocery Store"


def test_pdf_does_not_invent_a_year_for_yearless_dates():
    transactions = StatementParser()._extract_transactions_from_text(
        "02 Jan Grocery Store 12.50 DR", "bank_account"
    )
    assert transactions == []


def test_currency_codes_require_word_boundaries():
    parser = StatementParser()
    assert parser._extract_currency("AUDIBLE.COM 12.50") is None
    assert parser._extract_currency("AUD 12.50") == "AUD"


def test_vendor_normalization_does_not_truncate_real_names():
    assert vendor_normalizer.extract_vendor("MCDONALDS 1234") == "mcdonalds"
    assert vendor_normalizer.extract_vendor("THE GAP") == "the gap"
    assert vendor_normalizer.extract_vendor("IBERIA AIRLINES") == "iberia airlines"
    assert vendor_normalizer.extract_vendor("POST OFFICE") == "post office"
    assert vendor_normalizer.extract_vendor("VISAGE SALON") == "visage salon"
    assert vendor_normalizer.extract_vendor("APPLEBEES") == "applebees"
    assert vendor_normalizer.should_ignore("Total Wine") is False
    assert vendor_normalizer.should_ignore("Total purchases") is True
