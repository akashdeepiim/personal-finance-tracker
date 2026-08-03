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


def test_card_payment_and_refund_are_not_parsed_as_income():
    bank_content = (
        b"Date,Description,Debit,Credit\n"
        b"2024-01-02,Credit Card Payment,100.00,\n"
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
