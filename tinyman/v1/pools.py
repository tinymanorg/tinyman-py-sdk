import math
from base64 import b64encode
from algosdk.v2client.algod import AlgodClient
from .contracts import get_pool_logicsig
from tinyman.utils import get_state_int, get_state_bytes


def get_pool_info(client: AlgodClient, validator_app_id, asset1_id, asset2_id):
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, asset2_id)
    pool_address = pool_logicsig.address()
    account_info = client.account_info(pool_address)
    return get_pool_info_from_account_info(account_info)


def get_pool_info_from_account_info(account_info):
    validator_app_id = account_info['apps-local-state'][0]['id']
    validator_app_state = {x['key']: x['value'] for x in account_info['apps-local-state'][0]['key-value']}

    asset1_id = get_state_int(validator_app_state, 'a1')
    asset2_id = get_state_int(validator_app_state, 'a2')

    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, asset2_id)
    pool_address = pool_logicsig.address()

    assert(account_info['address'] == pool_address)

    asset1_reserves = get_state_int(validator_app_state, 's1')
    asset2_reserves = get_state_int(validator_app_state, 's2')
    issued_liquidity = get_state_int(validator_app_state, 'ilt')
    unclaimed_protocol_fees = get_state_int(validator_app_state, 'p')

    liquidity_asset = account_info['created-assets'][0]

    pool = {
        'address': pool_address,
        'asset1_id': asset1_id,
        'asset2_id': asset2_id,
        'liquidity_asset_id': liquidity_asset['index'],
        'liquidity_asset_name': liquidity_asset['params']['name'],
        'asset1_reserves': asset1_reserves,
        'asset2_reserves': asset2_reserves,
        'issued_liquidity': issued_liquidity,
        'unclaimed_protocol_fees': unclaimed_protocol_fees,
        'validator_app_id': validator_app_id,
        'round': account_info['round'],
    }
    return pool



class Pool:
    def __init__(self, client: AlgodClient, validator_app_id, asset1_id, asset2_id, info=None, fetch=True) -> None:
        self.client = client
        self.validator_app_id = validator_app_id
        self.asset1_id = asset1_id
        self.asset2_id = asset2_id

        self.liquidity_asset_id = None
        self.liquidity_asset_name = None
        self.asset1_reserves = None
        self.asset2_reserves = None
        self.issued_liquidity = None
        self.unclaimed_protocol_fees = None
        self.last_refreshed_round = None
        if fetch:
            self.refresh(info)
    
    @classmethod
    def from_account_info(cls, account_info):
        info = get_pool_info_from_account_info(account_info)
        pool = Pool(None, info['validator_app_id'], info['asset1_id'], info['asset2_id'], info)
        return pool

    def refresh(self, info=None):
        if info is None:
            info = get_pool_info(self.client, self.validator_app_id, self.asset1_id, self.asset2_id)
        self.liquidity_asset_id = info['liquidity_asset_id']
        self.liquidity_asset_name = info['liquidity_asset_name']
        self.asset1_reserves = info['asset1_reserves']
        self.asset2_reserves = info['asset2_reserves']
        self.issued_liquidity = info['issued_liquidity']
        self.unclaimed_protocol_fees = info['unclaimed_protocol_fees']
        self.last_refreshed_round = info['round']
    
    def get_logicsig(self):
        pool_logicsig = get_pool_logicsig(self.validator_app_id, self.asset1_id, self.asset2_id)
        return pool_logicsig
    
    @property
    def address(self):
        logicsig = self.get_logicsig()
        pool_address = logicsig.address()
        return pool_address

    @property
    def asset1_price(self):
        return self.asset2_reserves / self.asset1_reserves

    @property
    def asset2_price(self):
        return self.asset1_reserves / self.asset2_reserves

    def info(self):
        pool = {
            'address': self.address,
            'asset1_id': self.asset1_id,
            'asset2_id': self.asset2_id,
            'liquidity_asset_id': self.liquidity_asset_id,
            'liquidity_asset_name': self.liquidity_asset_name,
            'asset1_reserves': self.asset1_reserves,
            'asset2_reserves': self.asset2_reserves,
            'issued_liquidity': self.issued_liquidity,
            'unclaimed_protocol_fees': self.unclaimed_protocol_fees,
            'last_refreshed_round': self.last_refreshed_round,
        }
        return pool
    
    def mint_quote(self, asset1_amount=None, asset2_amount=None):
        if self.issued_liquidity > 0:
            if asset1_amount is None:
                asset1_amount = asset2_amount * self.asset2_price

            if asset2_amount is None:
                asset2_amount = asset1_amount * self.asset1_price

            liquidity_asset_amount = min(
                asset1_amount * self.issued_liquidity / self.asset1_reserves,
                asset2_amount * self.issued_liquidity / self.asset2_reserves,
            )
        else: # first mint
            liquidity_asset_amount = math.sqrt(self.asset1_amount * self.asset2_amount) - 1000

        return dict(
            asset1_amount=int(asset1_amount),
            asset2_amount=int(asset2_amount),
            liquidity_asset_amount=int(liquidity_asset_amount),
        )
    
    def swap_quote(self, asset_in, asset_in_amount=None, asset_out_amount=None, swap_type=None):
        if asset_in == self.asset1_id:
            input_supply = self.asset1_reserves
            output_supply = self.asset2_reserves
        else:
            input_supply = self.asset2_reserves
            output_supply = self.asset1_reserves
        
        # k = input_supply * output_supply
        # ignoring fees, k must remain constant 
        # (input_supply + asset_in) * (output_supply - amount_out) = k
        k = input_supply * output_supply

        if swap_type == 'fixed_input':
            asset_in_amount_minus_fee = (asset_in_amount * 997) / 1000
            swap_fees = asset_in_amount - asset_in_amount_minus_fee
            asset_out_amount = output_supply - (k / (input_supply + asset_in_amount_minus_fee))
        elif swap_type == 'fixed_output':
            calculated_amount_in_without_fee = (k / (output_supply - asset_out_amount)) - input_supply
            asset_in_amount = calculated_amount_in_without_fee * 1000/997
            swap_fees = asset_in_amount - calculated_amount_in_without_fee
        else:
            raise Exception('Unknown swap_type!')
        return dict(
            amount_in=int(asset_in_amount),
            amount_out=int(asset_out_amount),
            swap_fees=int(swap_fees),
            price=asset_out_amount/asset_in_amount,
            swap_type=swap_type,
        )
