from aiogram import Router, types

from config import logger
from services.coins import (
    CURRENCY_QUERY,
    crypto_api,
    fiat_api,
    get_change_emoji,
    parse_currency_query,
)

router = Router()


async def currency_query(message: types.Message) -> dict | bool:
    """Filter: matches only real conversion queries, injects `query` into the handler."""
    if not message.text or not CURRENCY_QUERY.match(message.text.strip()):
        return False
    if not fiat_api.rates:
        await fiat_api.update_rates()
    if not crypto_api.coin_list:
        await crypto_api.update_coin_list()

    parsed = parse_currency_query(message.text, fiat_api.rates, crypto_api.coin_list)
    return {"query": parsed} if parsed else False


@router.message(
    currency_query, flags={"log": "COINS_CONVERTER", "feature": "coins_converter_disabled"}
)
async def convert_currency(message: types.Message, query: tuple[float, str, str]):
    """Currency conversion handler"""
    amount, from_currency, to_currency = query
    try:
        # Try crypto conversion first
        crypto_price = await crypto_api.get_crypto_price_with_changes(from_currency, to_currency)
        if crypto_price and crypto_price.current_price:
            total = amount * crypto_price.current_price
            response = [
                f"<code>{amount:g} {from_currency.upper()} = {total:.2f} {to_currency.upper()}</code>",
                f"\n<b> - 24h Change:</b> {get_change_emoji(crypto_price.change_24h)} <code>{crypto_price.change_24h:.2f}%</code>",
                f"\n<b> - 7d Change:</b> {get_change_emoji(crypto_price.change_7d)} <code>{crypto_price.change_7d:.2f}%</code>",
            ]
            return await message.reply("".join(response))

        current_rate = await fiat_api.get_fiat_rate_with_change(from_currency, to_currency)
        if current_rate:
            total = amount * current_rate
            return await message.reply(
                f"<code>{amount:g} {from_currency.upper()} = {total:.2f} {to_currency.upper()}</code>"
            )

    except Exception as e:
        logger.error(f"Error in conversion handler: {e}")
    return False  # nothing sent: don't count it as a conversion
