"""
Script to clear all data from the database
"""

from database import SessionLocal
from models import Transaction, Statement, Analysis, CategoryLearning


def clear_all_data():
    """Delete all persisted finance and learning data."""
    db = SessionLocal()
    try:
        print("Clearing all data...")

        # Delete all transactions
        deleted_transactions = db.query(Transaction).delete()
        print(f"✓ Deleted {deleted_transactions} transactions")

        # Delete all statements
        deleted_statements = db.query(Statement).delete()
        print(f"✓ Deleted {deleted_statements} statements")

        # Delete all analyses
        deleted_analyses = db.query(Analysis).delete()
        print(f"✓ Deleted {deleted_analyses} analyses")

        deleted_rules = db.query(CategoryLearning).delete()
        print(f"✓ Deleted {deleted_rules} category learning rules")

        db.commit()
        print("\n✅ All data cleared successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    response = input("⚠️  WARNING: This will delete ALL data. Are you sure? (yes/no): ")
    if response.lower() == "yes":
        clear_all_data()
    else:
        print("Operation cancelled.")
