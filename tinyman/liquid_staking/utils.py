from decimal import Decimal

from tinyman.liquid_staking.constants import *
from tinyman.utils import get_global_state


def calculate_talgo_to_algo_ratio(algod):
    global_state = get_global_state(algod, MAINNET_TALGO_APP_ID)

    LIQUID_STAKING_NODE_ADDRESSES = [
        "EP2YRTCL3SAA7HYG7KKWUC6ZH36SLYIKOX4FORKXZLUUQASP5JDJP4UU5A",
        "D6CCE7DL3GSVOCQDPWMNR5V7JEKGXOJACCU4A4K76DLJHZ4H47WRVBPUNY",
        "UTTJ2JOAXXAZEMKFSRNKFW4OIPMETRORCHNCDEDAHBJ5THNZTLWS6ZLUYU",
        "3X3CIVGQGHVVGMJ627NQUXPN3EVLOR6ZPDXJ4XZGFW5DQVXFBGUKEKOEEI",
        "F66MBWKUEG5GXZB4HFIZJRSMNYOATH2URKQBTBKKI7ZJAA2IFUFKXLHTOA",
    ]
    app_account = LIQUID_STAKING_NODE_ADDRESSES[0]
    account_info = algod.account_info(app_account)

    algo_balance = account_info["amount"] - account_info["min-balance"]
    talgo_balance = account_info["assets"][0]["amount"] - global_state["protocol_talgo"]

    for address in LIQUID_STAKING_NODE_ADDRESSES[1:]:
        account_info = algod.account_info(address)
        algo_balance += (account_info["amount"] - account_info["min-balance"])

    TALGO_TOTAL_SUPPLY = 10_000_000_000_000_000
    minted_talgo = TALGO_TOTAL_SUPPLY - talgo_balance
    new_rewards = algo_balance - global_state["algo_balance"]
    protocol_rewards = (new_rewards * global_state["protocol_fee"]) / 100
    rate = Decimal(algo_balance - protocol_rewards) / Decimal(minted_talgo)

    return rate
