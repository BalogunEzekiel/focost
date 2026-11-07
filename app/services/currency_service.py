"""Currency metadata and deterministic monetary formatting."""

from decimal import Decimal, InvalidOperation


CURRENCIES = {
    "NGN": {
        "name": "Nigerian Naira",
        "symbol": "₦",
        "decimals": 2,
    },
    "USD": {
        "name": "US Dollar",
        "symbol": "$",
        "decimals": 2,
    },
    "GBP": {
        "name": "British Pound",
        "symbol": "£",
        "decimals": 2,
    },
    "EUR": {
        "name": "Euro",
        "symbol": "€",
        "decimals": 2,
    },
    "GHS": {
        "name": "Ghanaian Cedi",
        "symbol": "₵",
        "decimals": 2,
    },
    "KES": {
        "name": "Kenyan Shilling",
        "symbol": "KSh",
        "decimals": 2,
    },
    "ZAR": {
        "name": "South African Rand",
        "symbol": "R",
        "decimals": 2,
    },
    "CAD": {
        "name": "Canadian Dollar",
        "symbol": "C$",
        "decimals": 2,
    },
    "AUD": {
        "name": "Australian Dollar",
        "symbol": "A$",
        "decimals": 2,
    },
    "INR": {
        "name": "Indian Rupee",
        "symbol": "₹",
        "decimals": 2,
    },
}


class CurrencyService:

    @staticmethod
    def available():
        """Return supported currency metadata."""

        return CURRENCIES.copy()

    @staticmethod
    def set(user, code):
        """Set a user's supported display currency."""

        code = (code or "").strip().upper()

        if code not in CURRENCIES:
            raise ValueError("Unsupported currency.")

        user.currency = code

        return code

    @staticmethod
    def format(
        amount,
        currency="NGN",
        include_code=False,
    ):
        """
        Format an amount using the selected currency's symbol
        and configured decimal precision.

        This method formats the supplied amount; it does not
        alter or convert the amount.
        """

        code = (
            currency
            if currency in CURRENCIES
            else "NGN"
        )

        meta = CURRENCIES[code]

        try:
            value = Decimal(
                str(
                    amount
                    if amount is not None
                    else 0
                )
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            value = Decimal("0")

        rendered = (
            f"{value:,.{meta['decimals']}f}"
        )

        if include_code:
            return (
                f"{meta['symbol']}{rendered} {code}"
            )

        return f"{meta['symbol']}{rendered}"