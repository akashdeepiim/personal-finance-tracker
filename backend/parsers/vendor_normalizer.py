"""
Vendor Normalization Utility

Industry-standard vendor extraction and normalization for bank/credit card statements.
"""

import re
from typing import Optional, Tuple


class VendorNormalizer:
    """Extract and normalize vendor names from transaction descriptions"""
    
    # Common transaction prefixes to strip
    TRANSACTION_PREFIXES = [
        # Card network prefixes
        r'^VISA\s*\*?\s*',
        r'^MC\s*\*?\s*',
        r'^MASTERCARD\s*\*?\s*',
        r'^AMEX\s*\*?\s*',
        r'^DISCOVER\s*\*?\s*',
        r'^RUPAY\s*\*?\s*',
        # Payment processor prefixes
        r'^SQ\s*\*?\s*',           # Square
        r'^SQUARE\s*\*?\s*',
        r'^PAYPAL\s*\*?\s*',
        r'^PP\s*\*?\s*',
        r'^STRIPE\s*\*?\s*',
        r'^RAZORPAY\s*\*?\s*',
        r'^PAYTM\s*\*?\s*',
        r'^GPAY\s*\*?\s*',
        r'^PHONEPE\s*\*?\s*',
        # E-commerce prefixes  
        r'^AMZN\s*(?:MKTP|Mktp)?\s*(?:US|IN|UK)?\s*\*?\s*',
        r'^AMAZON\s*(?:PRIME|MKTP)?\s*\*?\s*',
        r'^FLIPKART\s*\*?\s*',
        # Subscription prefixes
        r'^GOOGLE\s*\*?\s*',
        r'^APPLE\.COM\s*',
        r'^APPLE\s*\*?\s*',
        # Other common prefixes
        r'^POS\s*(?:TXN|PURCHASE)?\s*',
        r'^DEBIT\s*CARD\s*',
        r'^CREDIT\s*CARD\s*',
        r'^IB\s*',  # Internet banking
        r'^MB\s*',  # Mobile banking
    ]
    
    # Suffixes to strip (reference numbers, dates, locations)
    SUFFIX_PATTERNS = [
        r'\s*#?\d{4,}$',           # Transaction reference numbers
        r'\s*-?\d{6,}$',           # Account/reference numbers
        r'\s*\*?\d{4}$',           # Card last 4 digits
        r'\s*\d{2}[/-]\d{2}[/-]\d{2,4}$',  # Dates
        r'\s*[A-Z]{2,3}\s*$',      # State/country codes
        r'\s*\d{5,6}$',            # Zip codes
        r'\s*\*+$',                # Trailing asterisks
    ]
    
    # Transaction type indicators
    TRANSACTION_TYPE_KEYWORDS = {
        'opening_balance': ['opening bal', 'opening balance', 'o/b', 'begin bal', 'beginning balance'],
        'closing_balance': ['closing bal', 'closing balance', 'c/b', 'end bal', 'ending balance'],
        'credit': ['refund', 'credit', 'reversal', 'cashback', 'cash back', 'cr', 'deposit', 'salary', 'payroll', 'direct dep'],
        'transfer': ['transfer', 'xfer', 'neft', 'imps', 'upi', 'rtgs', 'fund transfer', 'eft'],
        'fee': ['fee', 'charge', 'interest', 'service chg', 'annual fee', 'late fee', 'penalty'],
        'atm': ['atm', 'cash withdrawal', 'cash wdl', 'atm withdrawal'],
        'payment': ['payment', 'pmt', 'autopay', 'auto pay', 'bill payment', 'billpay'],
    }
    
    # Patterns to IGNORE (not actual transactions)
    IGNORE_PATTERNS = [
        # Totals and summaries
        'total', 'sub total', 'subtotal', 'grand total',
        'summary', 'statement summary', 'account summary',
        'balance brought forward', 'balance carried forward', 'b/f', 'c/f',
        # Column headers often picked up
        'date', 'description', 'particulars', 'narration', 'amount', 
        'debit', 'credit', 'balance', 'withdrawal', 'deposit',
        'transaction details', 'transaction date', 'value date',
        # Statement metadata
        'page', 'page no', 'statement period', 'account number', 'account no',
        'branch', 'ifsc', 'customer id', 'cif', 'account holder',
        # Interest and charges summaries
        'interest earned', 'interest paid', 'total charges', 'charges debited',
        'tax deducted', 'tds', 'gst',
        # Misc non-transactions
        'passbook', 'cheque book', 'chequebook', 'nominee',
        'minimum balance', 'average balance', 'available balance',
        'lien amount', 'hold amount', 'unclaimed',
    ]
    
    # Known vendor aliases/normalizations
    VENDOR_ALIASES = {
        'amzn': 'amazon',
        'amzn mktp': 'amazon marketplace',
        'amazn': 'amazon',
        'starbux': 'starbucks',
        'sbux': 'starbucks',
        'wmt': 'walmart',
        'wal-mart': 'walmart',
        'mcdonalds': 'mcdonalds',
        'mcd': 'mcdonalds',
        'uber trip': 'uber',
        'uber eats': 'uber eats',
        'uber*eats': 'uber eats',
        'lyft ride': 'lyft',
        'nflx': 'netflix',
        'spotfy': 'spotify',
        'drizly': 'drizly',
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._prefix_patterns = [re.compile(p, re.IGNORECASE) for p in self.TRANSACTION_PREFIXES]
        self._suffix_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUFFIX_PATTERNS]
    
    def extract_vendor(self, description: str) -> str:
        """
        Extract clean vendor name from transaction description.
        
        Args:
            description: Raw transaction description
            
        Returns:
            Normalized vendor name
        """
        if not description:
            return ""
        
        # Start with lowercase cleaned description
        cleaned = description.strip()
        
        # Remove transaction prefixes
        for pattern in self._prefix_patterns:
            cleaned = pattern.sub('', cleaned)
        
        # Remove suffixes (reference numbers, dates, etc.)
        for pattern in self._suffix_patterns:
            cleaned = pattern.sub('', cleaned)
        
        # Clean up whitespace and special characters
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        cleaned = re.sub(r'^[\*\-\.\s]+', '', cleaned)  # Leading special chars
        cleaned = re.sub(r'[\*\-\.\s]+$', '', cleaned)  # Trailing special chars
        cleaned = cleaned.strip()
        
        # Normalize to lowercase for matching
        vendor_lower = cleaned.lower()
        
        # Check for known aliases
        for alias, normalized in self.VENDOR_ALIASES.items():
            if alias in vendor_lower:
                return normalized
        
        # Return first 2-3 meaningful words as vendor name
        words = vendor_lower.split()
        meaningful_words = [w for w in words if len(w) > 1 and not w.isdigit()]
        
        if len(meaningful_words) >= 2:
            return ' '.join(meaningful_words[:3])
        elif meaningful_words:
            return meaningful_words[0]
        
        return cleaned.lower()[:50]  # Fallback to first 50 chars
    
    def should_ignore(self, description: str) -> bool:
        """
        Check if a description should be ignored (not a real transaction).
        
        Args:
            description: Transaction description
            
        Returns:
            True if this should be ignored
        """
        if not description:
            return True
        
        desc_lower = description.lower().strip()
        
        # Ignore very short descriptions
        if len(desc_lower) < 3:
            return True
        
        # Check against ignore patterns
        for pattern in self.IGNORE_PATTERNS:
            if pattern in desc_lower:
                return True
        
        # Ignore if description is mostly numbers
        alpha_chars = sum(1 for c in desc_lower if c.isalpha())
        if alpha_chars < 3:
            return True
        
        return False
    
    def detect_transaction_type(self, description: str, amount: float, account_type: str = 'bank') -> str:
        """
        Detect transaction type from description and amount.
        
        Args:
            description: Transaction description
            amount: Transaction amount (negative = outflow)
            account_type: 'bank' or 'credit_card'
            
        Returns:
            Transaction type: 'credit', 'debit', 'balance', or 'ignore'
        """
        desc_lower = description.lower()
        
        # First check if this should be ignored entirely
        if self.should_ignore(description):
            return 'ignore'
        
        # Check for balance entries (not actual transactions)
        for keyword in self.TRANSACTION_TYPE_KEYWORDS['opening_balance']:
            if keyword in desc_lower:
                return 'balance'
        for keyword in self.TRANSACTION_TYPE_KEYWORDS['closing_balance']:
            if keyword in desc_lower:
                return 'balance'
        
        # Check for explicit credit keywords
        for keyword in self.TRANSACTION_TYPE_KEYWORDS['credit']:
            if keyword in desc_lower:
                return 'credit'
        
        # Check for fee keywords (always a debit/expense)
        for keyword in self.TRANSACTION_TYPE_KEYWORDS['fee']:
            if keyword in desc_lower:
                return 'debit'
        
        # Determine from amount sign based on account type
        if account_type == 'credit_card':
            # Credit card: positive = purchase (debit), negative = payment/refund (credit)
            return 'credit' if amount < 0 else 'debit'
        else:
            # Bank account: positive = deposit (credit), negative = withdrawal (debit)
            return 'credit' if amount > 0 else 'debit'
    
    def get_transaction_subtype(self, description: str) -> Optional[str]:
        """
        Get specific transaction subtype (transfer, ATM, fee, payment, etc.)
        
        Args:
            description: Transaction description
            
        Returns:
            Subtype string or None
        """
        desc_lower = description.lower()
        
        for subtype, keywords in self.TRANSACTION_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    return subtype
        
        return None
    
    def match_vendors(self, description1: str, description2: str) -> Tuple[bool, float]:
        """
        Check if two transaction descriptions are from the same vendor.
        
        Args:
            description1: First transaction description
            description2: Second transaction description
            
        Returns:
            Tuple of (is_match, confidence)
        """
        vendor1 = self.extract_vendor(description1)
        vendor2 = self.extract_vendor(description2)
        
        if not vendor1 or not vendor2:
            return False, 0.0
        
        # Exact match
        if vendor1 == vendor2:
            return True, 1.0
        
        # One contains the other
        if vendor1 in vendor2 or vendor2 in vendor1:
            return True, 0.9
        
        # Check word overlap
        words1 = set(vendor1.split())
        words2 = set(vendor2.split())
        overlap = words1 & words2
        
        if len(overlap) >= 1:
            confidence = len(overlap) / max(len(words1), len(words2))
            return confidence >= 0.5, confidence
        
        return False, 0.0


# Singleton instance for easy import
vendor_normalizer = VendorNormalizer()
