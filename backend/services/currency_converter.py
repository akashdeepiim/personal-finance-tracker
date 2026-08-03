import requests
from typing import Dict
from datetime import datetime
import json
import os
import logging
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


class CurrencyConverter:
    """Currency conversion service using exchange rate API"""

    # Fallback rates (updated periodically, but using API is preferred)
    FALLBACK_RATES = {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "JPY": 149.50,
        "CAD": 1.35,
        "AUD": 1.52,
        "CHF": 0.88,
        "CNY": 7.24,
        "INR": 83.12,
        "MXN": 17.05,
        "BRL": 4.95,
        "ZAR": 18.65,
        "SGD": 1.34,
        "HKD": 7.82,
        "NZD": 1.68,
    }

    def __init__(self):
        self.cache_file = (
            Path(__file__).resolve().parents[1] / "currency_rates_cache.json"
        )
        self.cache_duration = 3600  # 1 hour cache
        self.rates_cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cached exchange rates"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)
                    return cache.get("rates", {})
            except (OSError, ValueError, TypeError):
                pass
        return {}

    def _save_cache(self, rates: Dict):
        """Save exchange rates to cache"""
        try:
            temporary = self.cache_file.with_suffix(".tmp")
            with open(temporary, "w") as f:
                json.dump({"rates": rates, "timestamp": datetime.now().timestamp()}, f)
            os.replace(temporary, self.cache_file)
        except (OSError, TypeError):
            pass

    def _fetch_rates(self) -> Dict:
        """Fetch current exchange rates from API"""
        try:
            # Using exchangerate-api.com (free, no API key required)
            response = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD", timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                rates = data.get("rates", {})
                rates["USD"] = 1.0  # Base currency
                self._save_cache(rates)
                return rates
        except (requests.RequestException, ValueError) as exc:
            logging.getLogger(__name__).warning(
                "Unable to refresh exchange rates: %s", exc
            )

        # Fallback to cached rates or default rates
        if self.rates_cache:
            return self.rates_cache
        return self.FALLBACK_RATES

    def _is_cache_expired(self) -> bool:
        """Check if the cache has expired"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)
                    return (
                        datetime.now().timestamp() - cache.get("timestamp", 0)
                        >= self.cache_duration
                    )
            except (OSError, ValueError, TypeError):
                return True
        return True

    def get_rates(self) -> Dict:
        """Get current exchange rates"""
        if not self.rates_cache or self._is_cache_expired():
            self.rates_cache = self._fetch_rates()
        return self.rates_cache

    def convert(self, amount, from_currency: str, to_currency: str = "USD") -> Decimal:
        """Convert amount from one currency to another"""
        rates = self.get_rates()
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        if from_currency not in rates or to_currency not in rates:
            raise ValueError(
                f"Unsupported currency conversion: {from_currency} to {to_currency}"
            )
        value = Decimal(str(amount))
        if from_currency == to_currency:
            return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # If converting from USD
        if from_currency == "USD":
            if to_currency in rates:
                return (value * Decimal(str(rates[to_currency]))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

        # If converting to USD
        if to_currency == "USD":
            if from_currency in rates:
                return (value / Decimal(str(rates[from_currency]))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

        # Converting between two non-USD currencies
        if from_currency in rates and to_currency in rates:
            # Convert to USD first, then to target currency
            usd_amount = value / Decimal(str(rates[from_currency]))
            return (usd_amount * Decimal(str(rates[to_currency]))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

    def get_supported_currencies(self) -> list:
        """Get list of supported currencies"""
        rates = self.get_rates()
        return sorted(list(rates.keys()))

    def format_currency(self, amount: float, currency: str) -> str:
        """Format amount with currency symbol"""
        currency = currency.upper()
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CAD": "C$",
            "AUD": "A$",
            "CHF": "CHF",
            "CNY": "¥",
            "INR": "₹",
            "MXN": "$",
            "BRL": "R$",
            "ZAR": "R",
            "SGD": "S$",
            "HKD": "HK$",
            "NZD": "NZ$",
        }

        symbol = symbols.get(currency, currency)

        # Format based on currency
        if currency in ["JPY", "KRW"]:
            return f"{symbol}{amount:,.0f}"
        else:
            return f"{symbol}{amount:,.2f}"
