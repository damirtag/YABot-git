import re
from datetime import datetime, timedelta
from typing import NamedTuple

from aiohttp import ClientSession

CURRENCY_QUERY = re.compile(
    r"^(?:(\d+(?:[.,]\d+)?)\s*)?([a-z]{2,6})(?:\s+(?:to\s+|in\s+|в\s+)?([a-z]{2,6}))?$",
    re.IGNORECASE,
)


def parse_currency_query(text: str, fiat_codes, crypto_symbols) -> tuple[float, str, str] | None:
    """
    Accepts "100 USD KZT", "100 usd to kzt", "usd kzt", "1 SOL" (target defaults to USD).
    Target must be a known fiat code, source a known fiat code or crypto symbol.
    Without an explicit target a crypto symbol must be uppercase: coin symbols
    cover plenty of everyday words ("5 min", "2 pm").
    """
    match = CURRENCY_QUERY.match(text.strip())
    if not match:
        return None
    amount, src, dst = match.groups()
    if amount is None and dst is None:
        return None

    target = (dst or "usd").upper()
    if target not in fiat_codes:
        return None
    if src.upper() not in fiat_codes:
        if src.lower() not in crypto_symbols or (dst is None and not src.isupper()):
            return None

    return float(amount.replace(",", ".")) if amount else 1.0, src.lower(), target.lower()


def get_change_emoji(change: float) -> str:
    """Return appropriate emoji based on price change"""
    if change > 5:
        return "🚀"  # Rocket for significant gain
    elif change > 0:
        return "📈"  # Chart up
    elif change < -5:
        return "📉💨"  # Chart down with wind
    elif change < 0:
        return "📉"  # Chart down
    return "➡️"  # Right arrow for no significant change


class PriceChange(NamedTuple):
    current_price: float
    change_24h: float
    change_7d: float


# symbols users type that CoinGecko lists under a different ticker
SYMBOL_ALIASES = {"ton": "the-open-network"}  # Toncoin is "gram" on CoinGecko


class CryptoAPI:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session: ClientSession | None = None
        self.coin_list: dict[str, str] = {}  # symbol -> id mapping

    async def init_session(self):
        """Initialize session and coin list"""
        if not self.session:
            self.session = ClientSession()
            await self.update_coin_list()

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def update_coin_list(self):
        """
        Update internal coin list mapping.
        Symbols collide (dozens of coins are "ton"), so the top coins by market cap
        claim their symbols first; the full list only fills in the rest.
        """
        if not self.session:
            await self.init_session()
        coin_list: dict[str, str] = dict(SYMBOL_ALIASES)
        try:
            params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 250}
            async with self.session.get(
                f"{self.base_url}/coins/markets", params=params
            ) as response:  # type: ignore
                if response.status == 200:
                    for coin in await response.json():
                        coin_list.setdefault(coin["symbol"].lower(), coin["id"])
                else:
                    print(f"Failed to get top coins: {response.status}")

            async with self.session.get(f"{self.base_url}/coins/list") as response:  # type: ignore
                if response.status == 200:
                    for coin in await response.json():
                        coin_list.setdefault(coin["symbol"].lower(), coin["id"])
                else:
                    print(f"Failed to update coin list: {response.status}")
        except Exception as e:
            print(f"Error updating coin list: {str(e)}")
        if len(coin_list) > len(SYMBOL_ALIASES):
            self.coin_list = coin_list

    async def get_crypto_price_with_changes(self, crypto: str, fiat: str) -> PriceChange | None:
        """Get crypto price and changes in specified fiat currency"""
        if not self.session:
            await self.init_session()

        crypto = crypto.lower()
        fiat = fiat.lower()

        if not self.coin_list:
            await self.update_coin_list()

        if crypto not in self.coin_list:
            return None

        coin_id = self.coin_list[crypto]
        url = f"{self.base_url}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }

        try:
            async with self.session.get(url, params=params) as response:  # type: ignore
                if response.status == 200:
                    data = await response.json()
                    market_data = data["market_data"]
                    return PriceChange(
                        current_price=market_data["current_price"].get(fiat, 0),
                        change_24h=market_data["price_change_percentage_24h_in_currency"].get(
                            fiat, 0
                        ),
                        change_7d=market_data["price_change_percentage_7d_in_currency"].get(
                            fiat, 0
                        ),
                    )
                print(f"Failed to get crypto price: {response.status}")
                return None
        except Exception as e:
            print(f"Error getting crypto price: {str(e)}")
            return None


class FiatAPI:
    def __init__(self):
        self.base_url = "https://open.er-api.com/v6/latest"
        self.session: ClientSession | None = None
        self.rates: dict[str, float] = {}
        self.last_update: datetime | None = None
        self.base_currency = "USD"

    async def init_session(self):
        """Initialize session and rates"""
        if not self.session:
            self.session = ClientSession()
            await self.update_rates()

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def update_rates(self):
        """Update exchange rates"""
        if not self.session:
            await self.init_session()

        try:
            async with self.session.get(f"{self.base_url}/{self.base_currency}") as response:  # type: ignore
                if response.status == 200:
                    data = await response.json()
                    self.rates = data["rates"]
                    self.last_update = datetime.now()
                else:
                    print(f"Failed to update rates: {response.status}")
        except Exception as e:
            print(f"Error updating rates: {str(e)}")

    async def get_fiat_rate_with_change(self, from_currency: str, to_currency: str) -> float | None:
        """Get current rate and its change from previous day"""
        if not self.session:
            await self.init_session()

        # Update rates if older than 1 hour
        if not self.last_update or datetime.now() - self.last_update > timedelta(hours=1):
            await self.update_rates()

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency not in self.rates or to_currency not in self.rates:
            return None

        current_rate = self.rates[to_currency] / self.rates[from_currency]

        return current_rate


crypto_api = CryptoAPI()
fiat_api = FiatAPI()


async def init_coins_apis():
    await crypto_api.init_session()
    await fiat_api.init_session()
