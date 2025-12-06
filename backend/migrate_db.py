"""
Database migration script to add new columns to existing database
"""
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def migrate_database():
    """Add new columns if they don't exist"""
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    
    with engine.connect() as conn:
        # Check if original_amount column exists in transactions table
        try:
            result = conn.execute(text("PRAGMA table_info(transactions)"))
            columns = [row[1] for row in result]
            
            if 'original_amount' not in columns:
                print("Adding original_amount column to transactions table...")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN original_amount REAL NOT NULL DEFAULT 0"))
                conn.commit()
                print("✓ Added original_amount column")
            
            if 'currency' not in columns:
                print("Adding currency column to transactions table...")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN currency VARCHAR NOT NULL DEFAULT 'USD'"))
                conn.commit()
                print("✓ Added currency column")
            
            # Update existing rows to set original_amount = amount if it's 0
            conn.execute(text("UPDATE transactions SET original_amount = amount WHERE original_amount = 0"))
            conn.commit()
            
        except Exception as e:
            print(f"Error checking/updating transactions table: {e}")
        
        # Check if currency column exists in statements table
        try:
            result = conn.execute(text("PRAGMA table_info(statements)"))
            columns = [row[1] for row in result]
            
            if 'currency' not in columns:
                print("Adding currency column to statements table...")
                conn.execute(text("ALTER TABLE statements ADD COLUMN currency VARCHAR NOT NULL DEFAULT 'USD'"))
                conn.commit()
                print("✓ Added currency column to statements")
        except Exception as e:
            print(f"Error checking/updating statements table: {e}")
    
    print("Migration completed!")

if __name__ == "__main__":
    migrate_database()

