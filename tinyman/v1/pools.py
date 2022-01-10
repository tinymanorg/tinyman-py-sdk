import math
from dataclasses import dataclass
from base64 import b64encode, b64decode
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import decode_address
from .contracts import get_pool_logicsig
from tinyman.utils import get_state_int, get_state_bytes
from tinyman.assets import Asset, AssetAmount
from .swap import prepare_swap_transactions
from .bootstrap import prepare_bootstrap_transactions
from .mint import prepare_mint_transactions
from .burn import prepare_burn_transactions
from .redeem import prepare_redeem_transactions
from .optin import prepare_asset_optin_transactions
from .fees import prepare_redeem_fees_transactions
from .client import TinymanClient
from tinyman.v1 import swap


def get_pool_info(client: AlgodClient, validator_app_id, asset1_id, asset2_id):
    pool_logicsig = get_pool_logicsig(validator_app_id, asset1_id, asset2_id)
    pool_address = pool_logicsig.address()
    account_info = client.account_info(pool_address)
    return get_pool_info_from_account_info(account_info)


def get_pool_info_from_account_info(account_info):
    try:
        validator_app_id = account_info['apps-local-state'][0]['id']
    except IndexError:
        return {}
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
    liquidity_asset_id = liquidity_asset['index']

    outstanding_asset1_amount = get_state_int(validator_app_state, b64encode(b'o' + (asset1_id).to_bytes(8, 'big')))
    outstanding_asset2_amount = get_state_int(validator_app_state, b64encode(b'o' + (asset2_id).to_bytes(8, 'big')))
    outstanding_liquidity_asset_amount = get_state_int(validator_app_state, b64encode(b'o' + (liquidity_asset_id).to_bytes(8, 'big')))

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
        'outstanding_asset1_amount': outstanding_asset1_amount,
        'outstanding_asset2_amount': outstanding_asset2_amount,
        'outstanding_liquidity_asset_amount': outstanding_liquidity_asset_amount,
        'validator_app_id': validator_app_id,
        'algo_balance': account_info['amount'],
        'round': account_info['round'],
    }
    return pool


def get_excess_asset_key(pool_address, asset_id):
    a = decode_address(pool_address)
    key = b64encode(a + b'e' + (asset_id).to_bytes(8, 'big'))
    return key


@dataclass
class SwapQuote:
    swap_type: str
    amount_in: AssetAmount
    amount_out: AssetAmount
    swap_fees: int
    slippage: float

    @property
    def amount_out_with_slippage(self) -> AssetAmount:
        if self.swap_type == 'fixed-output':
            return self.amount_out
        else:
            return self.amount_out - (self.amount_out * self.slippage)

    @property
    def amount_in_with_slippage(self) -> AssetAmount:
        if self.swap_type == 'fixed-input':
            return self.amount_in
        else:
            return self.amount_in + (self.amount_in * self.slippage)

    @property
    def price(self) -> float:
        return self.amount_out.amount / self.amount_in.amount

    @property
    def price_with_slippage(self) -> float:
        return self.amount_out_with_slippage.amount / self.amount_in_with_slippage.amount


@dataclass
class MintQuote:
    amounts_in: 'dict[AssetAmount]'
    liquidity_asset_amount: AssetAmount
    slippage: float

    @property
    def liquidity_asset_amount_with_slippage(self) -> int:
        return self.liquidity_asset_amount - (self.liquidity_asset_amount * self.slippage)


@dataclass
class BurnQuote:
    amounts_out: 'dict[AssetAmount]'
    liquidity_asset_amount: AssetAmount
    slippage: float

    @property
    def amounts_out_with_slippage(self) -> dict:
        out = {}
        for k in self.amounts_out:
            out[k] = self.amounts_out[k] - (self.amounts_out[k] * self.slippage)
        return out


class Pool:
    def __init__(self, client: TinymanClient, asset_a: Asset, asset_b: Asset, info=None, fetch=True, validator_app_id=None) -> None:
        self.client = client
        self.validator_app_id = validator_app_id if validator_app_id is not None else client.validator_app_id

        if isinstance(asset_a, int):
            asset_a = client.fetch_asset(asset_a)
        if isinstance(asset_b, int):
            asset_b = client.fetch_asset(asset_b)

        if asset_a.id > asset_b.id:
            self.asset1 = asset_a
            self.asset2 = asset_b
        else:
            self.asset1 = asset_b
            self.asset2 = asset_a

        self.exists = None
        self.liquidity_asset: Asset = None
        self.asset1_reserves = None
        self.asset2_reserves = None
        self.issued_liquidity = None
        self.unclaimed_protocol_fees = None
        self.outstanding_asset1_amount = None
        self.outstanding_asset2_amount = None
        self.last_refreshed_round = None

        if fetch:
            self.refresh()
        elif info is not None:
            self.update_from_info(info)
    
    @classmethod
    def from_account_info(cls, account_info, client=None):
        info = get_pool_info_from_account_info(account_info)
        pool = Pool(client, info['asset1_id'], info['asset2_id'], info, validator_app_id=info['validator_app_id'])
        return pool

    def refresh(self, info=None):
        if info is None:
            info = get_pool_info(self.client.algod, self.validator_app_id, self.asset1.id, self.asset2.id)
            if not info:
                return
        self.update_from_info(info)
    
    def update_from_info(self, info):
        if info['liquidity_asset_id'] is not None:
            self.exists = True
        self.liquidity_asset = Asset(info['liquidity_asset_id'], name=info['liquidity_asset_name'], unit_name='TM1POOL', decimals=6)
        self.asset1_reserves = info['asset1_reserves']
        self.asset2_reserves = info['asset2_reserves']
        self.issued_liquidity = info['issued_liquidity']
        self.unclaimed_protocol_fees = info['unclaimed_protocol_fees']
        self.outstanding_asset1_amount = info['outstanding_asset1_amount']
        self.outstanding_asset2_amount = info['outstanding_asset2_amount']
        self.outstanding_liquidity_asset_amount = info['outstanding_liquidity_asset_amount']
        self.last_refreshed_round = info['round']

        self.algo_balance = info['algo_balance']
        self.min_balance = self.get_minimum_balance()
        if self.asset2.id == 0:
            self.asset2_reserves = (self.algo_balance - self.min_balance) - self.outstanding_asset2_amount
    
    def get_logicsig(self):
        pool_logicsig = get_pool_logicsig(self.validator_app_id, self.asset1.id, self.asset2.id)
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
            'asset1_id': self.asset1.id,
            'asset2_id': self.asset2.id,
            'asset1_unit_name': self.asset1.unit_name,
            'asset2_unit_name': self.asset2.unit_name,
            'liquidity_asset_id': self.liquidity_asset.id,
            'liquidity_asset_name': self.liquidity_asset.name,
            'asset1_reserves': self.asset1_reserves,
            'asset2_reserves': self.asset2_reserves,
            'issued_liquidity': self.issued_liquidity,
            'unclaimed_protocol_fees': self.unclaimed_protocol_fees,
            'outstanding_asset1_amount': self.outstanding_asset1_amount,
            'outstanding_asset2_amount': self.outstanding_asset2_amount,
            'outstanding_liquidity_asset_amount': self.outstanding_liquidity_asset_amount,
            'last_refreshed_round': self.last_refreshed_round,
        }
        return pool

    def convert(self, amount: AssetAmount):
        if amount.asset == self.asset1:
            return AssetAmount(self.asset2, int(amount.amount * self.asset1_price))
        elif amount.asset == self.asset2:
            return AssetAmount(self.asset1, int(amount.amount * self.asset2_price))
    
    def fetch_mint_quote(self, amount_a: AssetAmount, amount_b: AssetAmount=None, slippage=0.05):
        amount1 = amount_a if amount_a.asset == self.asset1 else amount_b
        amount2 = amount_a if amount_a.asset == self.asset2 else amount_b
        self.refresh()
        if not self.exists:
            raise Exception('Pool has not been bootstrapped yet!')
        if self.issued_liquidity:
            if amount1 is None:
                amount1 = self.convert(amount2)

            if amount2 is None:
                amount2 = self.convert(amount1)

            liquidity_asset_amount = min(
                amount1.amount * self.issued_liquidity / self.asset1_reserves,
                amount2.amount * self.issued_liquidity / self.asset2_reserves,
            )
        else: # first mint
            if not amount1 or not amount2:
                raise Exception('Amounts required for both assets for first mint!')
            liquidity_asset_amount = math.sqrt(amount1.amount * amount2.amount) - 1000
            # don't apply slippage tolerance to first mint
            slippage = 0

        quote = MintQuote(
            amounts_in={
                self.asset1: amount1,
                self.asset2: amount2,
            },
            liquidity_asset_amount=AssetAmount(self.liquidity_asset, liquidity_asset_amount),
            slippage=slippage,
        )
        return quote

    def fetch_burn_quote(self, liquidity_asset_in, slippage=0.05):
        if isinstance(liquidity_asset_in, int):
            liquidity_asset_in = AssetAmount(self.liquidity_asset, liquidity_asset_in)
        self.refresh()
        asset1_amount = (liquidity_asset_in.amount * self.asset1_reserves) / self.issued_liquidity
        asset2_amount = (liquidity_asset_in.amount * self.asset2_reserves) / self.issued_liquidity

        quote = BurnQuote(
            amounts_out={
                self.asset1: AssetAmount(self.asset1, asset1_amount),
                self.asset2: AssetAmount(self.asset2, asset2_amount),
            },
            liquidity_asset_amount=liquidity_asset_in,
            slippage=slippage,
        )
        return quote

    def fetch_fixed_input_swap_quote(self, amount_in: AssetAmount, slippage=0.05) -> SwapQuote:
        asset_in, asset_in_amount = amount_in.asset, amount_in.amount
        self.refresh()
        if asset_in == self.asset1:
            asset_out = self.asset2
            input_supply = self.asset1_reserves
            output_supply = self.asset2_reserves
        else:
            asset_out = self.asset1
            input_supply = self.asset2_reserves
            output_supply = self.asset1_reserves

        if not input_supply or not output_supply:
            raise Exception('Pool has no liquidity!')
        
        # k = input_supply * output_supply
        # ignoring fees, k must remain constant 
        # (input_supply + asset_in) * (output_supply - amount_out) = k
        k = input_supply * output_supply
        asset_in_amount_minus_fee = (asset_in_amount * 997) / 1000
        swap_fees = asset_in_amount - asset_in_amount_minus_fee
        asset_out_amount = output_supply - (k / (input_supply + asset_in_amount_minus_fee))

        amount_out = AssetAmount(asset_out, int(asset_out_amount))

        quote = SwapQuote(
            swap_type='fixed-input',
            amount_in=amount_in,
            amount_out=amount_out,
            swap_fees=AssetAmount(amount_in.asset, int(swap_fees)),
            slippage=slippage,
        )
        return quote

    def fetch_fixed_output_swap_quote(self, amount_out: AssetAmount, slippage=0.05) -> SwapQuote:
        asset_out, asset_out_amount = amount_out.asset, amount_out.amount
        self.refresh()
        if asset_out == self.asset1:
            asset_in = self.asset2
            input_supply = self.asset2_reserves
            output_supply = self.asset1_reserves
        else:
            asset_in = self.asset1
            input_supply = self.asset1_reserves
            output_supply = self.asset2_reserves
        
        # k = input_supply * output_supply
        # ignoring fees, k must remain constant 
        # (input_supply + asset_in) * (output_supply - amount_out) = k
        k = input_supply * output_supply

        calculated_amount_in_without_fee = (k / (output_supply - asset_out_amount)) - input_supply
        asset_in_amount = calculated_amount_in_without_fee * 1000/997
        swap_fees = asset_in_amount - calculated_amount_in_without_fee

        amount_in = AssetAmount(asset_in, int(asset_in_amount))

        quote = SwapQuote(
            swap_type='fixed-output',
            amount_out=amount_out,
            amount_in=amount_in,
            swap_fees=AssetAmount(amount_in.asset, int(swap_fees)),
            slippage=slippage,
        )

        return quote

    def prepare_swap_transactions(self, amount_in: AssetAmount, amount_out: AssetAmount, swap_type, swapper_address=None):
        swapper_address = swapper_address or self.client.user_address
        suggested_params = self.client.algod.suggested_params()
        txn_group = prepare_swap_transactions(
            validator_app_id=self.validator_app_id,
            asset1_id=self.asset1.id,
            asset2_id=self.asset2.id,
            liquidity_asset_id=self.liquidity_asset.id,
            asset_in_id=amount_in.asset.id,
            asset_in_amount=amount_in.amount,
            asset_out_amount=amount_out.amount, 
            swap_type=swap_type, 
            sender=swapper_address,
            suggested_params=suggested_params,
        )
        return txn_group
    
    def prepare_swap_transactions_from_quote(self, quote: SwapQuote, swapper_address=None):
        return self.prepare_swap_transactions(
            amount_in=quote.amount_in_with_slippage,
            amount_out=quote.amount_out_with_slippage,
            swap_type=quote.swap_type,
            swapper_address=swapper_address,
        )

    def prepare_bootstrap_transactions(self, pooler_address=None):
        pooler_address = pooler_address or self.client.user_address
        suggested_params = self.client.algod.suggested_params()
        txn_group = prepare_bootstrap_transactions(
            validator_app_id=self.validator_app_id,
            asset1_id=self.asset1.id,
            asset2_id=self.asset2.id,
            asset1_unit_name=self.asset1.unit_name,
            asset2_unit_name=self.asset2.unit_name,
            sender=pooler_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_mint_transactions(self, amounts_in: "dict[Asset, AssetAmount]", liquidity_asset_amount: AssetAmount, pooler_address=None):
        pooler_address = pooler_address or self.client.user_address
        asset1_amount = amounts_in[self.asset1]
        asset2_amount = amounts_in[self.asset2]
        suggested_params = self.client.algod.suggested_params()
        txn_group = prepare_mint_transactions(
            validator_app_id=self.validator_app_id,
            asset1_id=self.asset1.id,
            asset2_id=self.asset2.id,
            liquidity_asset_id=self.liquidity_asset.id,
            asset1_amount=asset1_amount.amount,
            asset2_amount=asset2_amount.amount,
            liquidity_asset_amount=liquidity_asset_amount.amount,
            sender=pooler_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_mint_transactions_from_quote(self, quote: MintQuote, pooler_address=None):
        return self.prepare_mint_transactions(
            amounts_in=quote.amounts_in,
            liquidity_asset_amount=quote.liquidity_asset_amount_with_slippage,
            pooler_address=pooler_address,
        )

    def prepare_burn_transactions(self, liquidity_asset_amount: AssetAmount, amounts_out, pooler_address=None):
        if isinstance(liquidity_asset_amount, int):
            liquidity_asset_amount = AssetAmount(self.liquidity_asset, liquidity_asset_amount)
        pooler_address = pooler_address or self.client.user_address
        asset1_amount = amounts_out[self.asset1]
        asset2_amount = amounts_out[self.asset2]
        suggested_params = self.client.algod.suggested_params()
        txn_group = prepare_burn_transactions(
            validator_app_id=self.validator_app_id,
            asset1_id=self.asset1.id,
            asset2_id=self.asset2.id,
            liquidity_asset_id=self.liquidity_asset.id,
            asset1_amount=asset1_amount.amount,
            asset2_amount=asset2_amount.amount,
            liquidity_asset_amount=liquidity_asset_amount.amount,
            sender=pooler_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_burn_transactions_from_quote(self, quote: BurnQuote, pooler_address=None):
        return self.prepare_burn_transactions(
            liquidity_asset_amount=quote.liquidity_asset_amount,
            amounts_out=quote.amounts_out_with_slippage,
            pooler_address=pooler_address,
        )

    def prepare_redeem_transactions(self, amount_out: AssetAmount, user_address=None):
        user_address = user_address or self.client.user_address
        suggested_params = self.client.algod.suggested_params()
        txn_group = prepare_redeem_transactions(
            validator_app_id=self.validator_app_id,
            asset1_id=self.asset1.id,
            asset2_id=self.asset2.id,
            liquidity_asset_id=self.liquidity_asset.id,
            asset_id=amount_out.asset.id,
            asset_amount=amount_out.amount,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_liquidity_asset_optin_transactions(self, user_address=None):
        user_address = user_address or self.client.user_address
        suggested_params = self.client.algod.suggested_params()
        txn_group = prepare_asset_optin_transactions(
            asset_id=self.liquidity_asset.id,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group
    
    def prepare_redeem_fees_transactions(self, amount, creator, user_address=None):
        user_address = user_address or self.client.user_address
        suggested_params = self.client.algod.suggested_params()
        txn_group = prepare_redeem_fees_transactions(
            validator_app_id=self.validator_app_id,
            asset1_id=self.asset1.id,
            asset2_id=self.asset2.id,
            liquidity_asset_id=self.liquidity_asset.id,
            amount=amount,
            creator=creator,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def get_minimum_balance(self):
        MIN_BALANCE_PER_ACCOUNT = 100000
        MIN_BALANCE_PER_ASSET = 100000
        MIN_BALANCE_PER_APP = 100000
        MIN_BALANCE_PER_APP_BYTESLICE = 50000
        MIN_BALANCE_PER_APP_UINT = 28500

        num_assets = 2 if self.asset2.id == 0 else 3
        num_created_apps = 0
        num_local_apps = 1
        total_uints = 16
        total_byteslices = 0

        total = MIN_BALANCE_PER_ACCOUNT + \
        (MIN_BALANCE_PER_ASSET * num_assets) + \
        (MIN_BALANCE_PER_APP * (num_created_apps + num_local_apps)) + \
        (MIN_BALANCE_PER_APP_UINT * total_uints) + \
        (MIN_BALANCE_PER_APP_BYTESLICE * total_byteslices)
        return total

    def fetch_excess_amounts(self, user_address=None):
        user_address = user_address or self.client.user_address
        pool_excess = self.client.fetch_excess_amounts(user_address).get(self.address, {})
        return pool_excess
    
    def fetch_pool_position(self, pooler_address=None):
        pooler_address = pooler_address or self.client.user_address
        account_info = self.client.algod.account_info(pooler_address)
        assets = {a['asset-id']: a for a in account_info['assets']}
        liquidity_asset_amount = assets.get(self.liquidity_asset.id, {}).get('amount', 0)
        quote = self.fetch_burn_quote(liquidity_asset_amount)
        return {
            self.asset1: quote.amounts_out[self.asset1],
            self.asset2: quote.amounts_out[self.asset2],
            self.liquidity_asset: quote.liquidity_asset_amount,
            'share': (liquidity_asset_amount / self.issued_liquidity),
        }

    def fetch_state(self, key=None):
        account_info = self.client.algod.account_info(self.address)
        try:
            validator_app_id = account_info['apps-local-state'][0]['id']
        except IndexError:
            return {}
        validator_app_state = {x['key']: x['value'] for x in account_info['apps-local-state'][0]['key-value']}

        if key:
            return get_state_int(validator_app_state, key)
        else:
            return validator_app_state

