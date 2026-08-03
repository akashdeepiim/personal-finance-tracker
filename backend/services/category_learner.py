from typing import Optional, Dict
from sqlalchemy.orm import Session
from models import CategoryLearning, Transaction

# Import vendor normalizer for better vendor matching
try:
    from parsers.vendor_normalizer import vendor_normalizer
except ImportError:
    vendor_normalizer = None


class CategoryLearner:
    """Learn from user category assignments and auto-tag similar transactions"""

    def __init__(self):
        pass

    def learn_from_transaction(self, db: Session, transaction: Transaction):
        """Learn category from a transaction"""
        try:
            description = transaction.description.lower()

            # Use vendor normalizer if available for better extraction
            if vendor_normalizer:
                vendor_pattern = vendor_normalizer.extract_vendor(description)
            else:
                # Fallback: first few words
                words = description.split()
                vendor_pattern = (
                    " ".join(words[:3]) if len(words) >= 3 else description[:30]
                )

            # Escape LIKE special characters
            escaped_pattern = vendor_pattern.replace("%", "\\%").replace("_", "\\_")

            # Check if we already have a learning rule for this pattern
            existing = (
                db.query(CategoryLearning)
                .filter(CategoryLearning.vendor_pattern.like(f"%{escaped_pattern}%"))
                .first()
            )

            if existing:
                # Update existing rule - increase confidence and usage
                if existing.category == transaction.category:
                    existing.usage_count += 1
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                else:
                    # Category changed - update it
                    existing.category = transaction.category or "Other"
                    existing.subcategory = transaction.subcategory
                    existing.transaction_type = getattr(
                        transaction, "transaction_type", "debit"
                    )
                    existing.usage_count = 1
                    existing.confidence = 0.5
            else:
                # Create new learning rule
                learning_rule = CategoryLearning(
                    vendor_pattern=vendor_pattern,
                    description_pattern=description[:50],
                    category=transaction.category or "Other",
                    subcategory=transaction.subcategory,
                    transaction_type=getattr(transaction, "transaction_type", "debit"),
                    confidence=0.7,
                    usage_count=1,
                )
                db.add(learning_rule)

            db.flush()
        except Exception as e:
            raise RuntimeError("Unable to save category learning rule") from e

    def update_matching_transactions(
        self,
        db: Session,
        transaction: Transaction,
        category: str,
        subcategory: str = None,
        transaction_type: str = None,
    ) -> int:
        """
        Update all transactions that match the same vendor as the given transaction.

        Returns:
            Number of transactions updated
        """
        try:
            description = transaction.description.lower()

            # Extract vendor pattern
            if vendor_normalizer:
                vendor = vendor_normalizer.extract_vendor(description)
            else:
                words = description.split()
                vendor = " ".join(words[:3]) if len(words) >= 3 else description[:30]

            if not vendor or len(vendor) < 2:
                return 0

            # Find all transactions with matching vendor
            # Use case-insensitive LIKE search
            first_token = vendor.split()[0].replace("%", "\\%").replace("_", "\\_")
            all_transactions = (
                db.query(Transaction)
                .filter(Transaction.description.ilike(f"%{first_token}%", escape="\\"))
                .all()
            )
            updated_count = 0

            for t in all_transactions:
                if t.id == transaction.id:
                    continue  # Skip the original transaction (already updated)

                # Check if vendors match
                if vendor_normalizer:
                    is_match, confidence = vendor_normalizer.match_vendors(
                        transaction.description, t.description
                    )
                    if is_match and confidence >= 0.7:
                        # Update this transaction
                        t.category = category
                        if subcategory:
                            t.subcategory = subcategory
                        if transaction_type:
                            t.transaction_type = transaction_type
                        updated_count += 1
                else:
                    # Fallback: simple substring match
                    t_vendor = " ".join(t.description.lower().split()[:3])
                    if vendor in t_vendor or t_vendor in vendor:
                        t.category = category
                        if subcategory:
                            t.subcategory = subcategory
                        if transaction_type:
                            t.transaction_type = transaction_type
                        updated_count += 1

            db.flush()
            return updated_count

        except Exception as e:
            raise RuntimeError("Unable to update matching transactions") from e

    def suggest_category(
        self, db: Session, description: str, amount: float, account_type: str
    ) -> Optional[Dict]:
        """Suggest category based on learned patterns"""
        description_lower = description.lower()
        best_match = None
        best_score = 0.0
        for word in description_lower.split()[:3]:
            if len(word) < 2:
                continue
            escaped = word.replace("%", "\\%").replace("_", "\\_")
            matches = (
                db.query(CategoryLearning)
                .filter(
                    CategoryLearning.vendor_pattern.ilike(f"%{escaped}%", escape="\\")
                )
                .limit(25)
                .all()
            )
            for match in matches:
                score = match.confidence * (match.usage_count / 10.0)
                if match.vendor_pattern.lower() in description_lower:
                    score *= 1.5
                if score > best_score:
                    best_score = score
                    best_match = match
        if best_match and best_score > 0.3:
            return {
                "category": best_match.category,
                "subcategory": best_match.subcategory,
                "transaction_type": best_match.transaction_type,
                "confidence": min(1.0, best_score),
            }
        return None

    def get_learning_rules(self, db: Session, limit: int = 200) -> list:
        """Get all learning rules"""
        rules = (
            db.query(CategoryLearning)
            .order_by(
                CategoryLearning.usage_count.desc(), CategoryLearning.confidence.desc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "id": r.id,
                "vendor_pattern": r.vendor_pattern,
                "category": r.category,
                "subcategory": r.subcategory,
                "transaction_type": r.transaction_type,
                "confidence": r.confidence,
                "usage_count": r.usage_count,
            }
            for r in rules
        ]
