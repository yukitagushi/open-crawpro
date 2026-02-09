from gamma import extract_yes_no_token_ids


def test_extract_yes_no_from_outcomes_tokenId():
    market = {
        "outcomes": [
            {"name": "Yes", "tokenId": "111"},
            {"name": "No", "tokenId": "222"},
        ]
    }
    yes, no = extract_yes_no_token_ids(market)
    assert yes == "111"
    assert no == "222"


def test_extract_yes_no_from_outcomeTokens_token_id():
    market = {
        "outcomeTokens": [
            {"outcome": "Yes", "token_id": 333},
            {"outcome": "No", "token_id": 444},
        ]
    }
    yes, no = extract_yes_no_token_ids(market)
    assert yes == "333"
    assert no == "444"
