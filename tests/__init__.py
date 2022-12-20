from algosdk.future.transaction import SuggestedParams


def get_suggested_params():
    sp = SuggestedParams(
        fee=1000, first=1, last=1000, min_fee=1000, flat_fee=True, gh="test"
    )
    return sp
