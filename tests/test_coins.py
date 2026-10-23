from services.coins import parse_currency_query

FIAT = {"USD", "KZT", "RUB", "EUR"}
CRYPTO = {"sol", "ton", "min", "pm", "eth"}


def parse(text):
    return parse_currency_query(text, FIAT, CRYPTO)


def test_accepts_conversion_queries():
    assert parse("100 USD KZT") == (100.0, "usd", "kzt")
    assert parse("50 eur to rub") == (50.0, "eur", "rub")
    assert parse("1,5 ton rub") == (1.5, "ton", "rub")
    assert parse("usd kzt") == (1.0, "usd", "kzt")
    assert parse("1 SOL") == (1.0, "sol", "usd")
    assert parse("100 eur") == (100.0, "eur", "usd")


def test_ignores_regular_chat():
    for text in ["hello", "ok bro", "привет", "5 min", "2 pm", "100", "lol kzt", "100 usd xyz"]:
        assert parse(text) is None, text
