from typing import Optional, Dict
from sqlalchemy.orm import Session
from models import CategoryLearning, Transaction
import re

class CategoryLearner:
    """Learn from user category assignments and auto-tag similar transactions"""
    
    def __init__(self):
        pass
    
    def learn_from_transaction(self, db: Session, transaction: Transaction):
        """Learn category from a transaction"""
        try:
            description = transaction.description.lower()
            
            # Extract vendor/merchant name (usually first few words)
            words = description.split()
            vendor_pattern = ' '.join(words[:3]) if len(words) >= 3 else description[:30]
            
            # Check if we already have a learning rule for this pattern
            existing = db.query(CategoryLearning).filter(
                CategoryLearning.vendor_pattern.like(f"%{vendor_pattern}%")
            ).first()
            
            if existing:
                # Update existing rule - increase confidence and usage
                if existing.category == transaction.category:
                    existing.usage_count += 1
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                else:
                    # Category changed - update it
                    existing.category = transaction.category or "Other"
                    existing.subcategory = transaction.subcategory
                    existing.transaction_type = getattr(transaction, 'transaction_type', 'debit')
                    existing.usage_count = 1
                    existing.confidence = 0.5
            else:
                # Create new learning rule
                learning_rule = CategoryLearning(
                    vendor_pattern=vendor_pattern,
                    description_pattern=description[:50],
                    category=transaction.category or "Other",
                    subcategory=transaction.subcategory,
                    transaction_type=getattr(transaction, 'transaction_type', 'debit'),
                    confidence=0.7,
                    usage_count=1
                )
                db.add(learning_rule)
            
            db.commit()
        except Exception as e:
            print(f"Error learning from transaction: {e}")
            db.rollback()
    
    def suggest_category(self, db: Session, description: str, amount: float, account_type: str) -> Optional[Dict]:
        """Suggest category based on learned patterns"""
        try:
            description_lower = description.lower()
            words = description_lower.split()
            
            # Try to match vendor patterns
            best_match = None
            best_score = 0.0
            
            # Check for exact or partial vendor matches
            for word in words[:3]:  # Check first 3 words
                if len(word) < 2:  # Skip very short words
                    continue
                try:
                    # SQLite uses LIKE (case-insensitive with COLLATE NOCASE)
                    matches = db.query(CategoryLearning).filter(
                        CategoryLearning.vendor_pattern.like(f"%{word}%")
                    ).all()
                    
                    for match in matches:
                        # Calculate match score
                        score = match.confidence * (match.usage_count / 10.0)  # Normalize usage count
                        
                        # Boost score if description contains vendor pattern
                        if match.vendor_pattern.lower() in description_lower:
                            score *= 1.5
                        
                        if score > best_score:
                            best_score = score
                            best_match = match
                except Exception as e:
                    # If query fails, continue without learning
                    print(f"Error querying category learning: {e}")
                    continue
            
            if best_match and best_score > 0.3:  # Minimum confidence threshold
                return {
                    'category': best_match.category,
                    'subcategory': best_match.subcategory,
                    'transaction_type': best_match.transaction_type,
                    'confidence': min(1.0, best_score)
                }
        except Exception as e:
            print(f"Error in suggest_category: {e}")
        
        return None
    
    def get_learning_rules(self, db: Session) -> list:
        """Get all learning rules"""
        rules = db.query(CategoryLearning).order_by(
            CategoryLearning.usage_count.desc(),
            CategoryLearning.confidence.desc()
        ).all()
        
        return [
            {
                'id': r.id,
                'vendor_pattern': r.vendor_pattern,
                'category': r.category,
                'subcategory': r.subcategory,
                'transaction_type': r.transaction_type,
                'confidence': r.confidence,
                'usage_count': r.usage_count
            }
            for r in rules
        ]

