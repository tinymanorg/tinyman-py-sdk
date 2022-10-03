from algosdk.v2client.algod import AlgodClient


def get_algod():
    # return AlgodClient(
    #     "<TOKEN>", "http://localhost:8080", headers={"User-Agent": "algosdk"}
    # )
    return AlgodClient("", "https://testnet-api.algonode.network")
