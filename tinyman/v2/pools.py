from typing import Optional

from algosdk.future.transaction import LogicSigAccount, Transaction, SuggestedParams
from algosdk.v2client.algod import AlgodClient

from tinyman.assets import Asset, AssetAmount
from tinyman.optin import prepare_asset_optin_transactions
from tinyman.utils import TransactionGroup
from .add_liquidity import (
    prepare_initial_add_liquidity_transactions,
    prepare_single_asset_add_liquidity_transactions,
    prepare_flexible_add_liquidity_transactions,
)
from .bootstrap import prepare_bootstrap_transactions
from .client import TinymanV2Client
from .constants import MIN_POOL_BALANCE_ASA_ALGO_PAIR, MIN_POOL_BALANCE_ASA_ASA_PAIR
from .contracts import get_pool_logicsig
from .exceptions import (
    AlreadyBootstrapped,
    BootstrapIsRequired,
    PoolHasNoLiquidity,
    PoolAlreadyHasLiquidity,
)
from .fees import (
    prepare_claim_fees_transactions,
    prepare_set_fee_transactions,
)
from .flash_loan import prepare_flash_loan_transactions
from .formulas import (
    calculate_subsequent_add_liquidity,
    calculate_initial_add_liquidity,
    calculate_fixed_input_swap,
    calculate_remove_liquidity_output_amounts,
    calculate_fixed_output_swap,
    calculate_flash_loan_payment_amount,
    calculate_fixed_input_fee_amount,
)
from .quotes import (
    FlexibleAddLiquidityQuote,
    SingleAssetAddLiquidityQuote,
    InitialAddLiquidityQuote,
    RemoveLiquidityQuote,
    InternalSwapQuote,
    SingleAssetRemoveLiquidityQuote,
    SwapQuote,
    FlashLoanQuote,
)
from .remove_liquidity import (
    prepare_remove_liquidity_transactions,
    prepare_single_asset_remove_liquidity_transactions,
)
from .swap import prepare_swap_transactions
from .utils import get_state_from_account_info


def generate_pool_info(address, validator_app_id, round_number, state):
    return {
        "address": address,
        "validator_app_id": validator_app_id,
        "round": round_number,
        **state,
    }


def get_pool_info(
    client: AlgodClient, validator_app_id: int, asset_1_id: int, asset_2_id: int
) -> dict:
    pool_logicsig = get_pool_logicsig(validator_app_id, asset_1_id, asset_2_id)
    pool_address = pool_logicsig.address()
    account_info = client.account_info(pool_address)
    pool_state = get_pool_state_from_account_info(account_info)

    return generate_pool_info(
        address=pool_address,
        validator_app_id=validator_app_id,
        round_number=account_info.get("round"),
        state=pool_state,
    )


def get_validator_app_id_from_account_info(account_info: dict) -> Optional[int]:
    try:
        return account_info["apps-local-state"][0]["id"]
    except IndexError:
        return None


def get_pool_state_from_account_info(account_info: dict) -> dict:
    if validator_app_id := get_validator_app_id_from_account_info(account_info):
        return get_state_from_account_info(account_info, validator_app_id)
    return {}


class Pool:
    def __init__(
        self,
        client: TinymanV2Client,
        asset_a: [Asset, int],
        asset_b: [Asset, int],
        info=None,
        fetch=True,
        validator_app_id=None,
    ) -> None:
        self.client = client
        self.validator_app_id = (
            validator_app_id
            if validator_app_id is not None
            else client.validator_app_id
        )

        if isinstance(asset_a, int):
            if fetch:
                asset_a = client.fetch_asset(asset_a)
            else:
                asset_a = Asset(id=asset_a)
        if isinstance(asset_b, int):
            if fetch:
                asset_b = client.fetch_asset(asset_b)
            else:
                asset_b = Asset(id=asset_b)

        if asset_a.id > asset_b.id:
            self.asset_1 = asset_a
            self.asset_2 = asset_b
        else:
            self.asset_1 = asset_b
            self.asset_2 = asset_a

        self.exists = None
        self.pool_token_asset: Asset = None
        self.asset_1_reserves = None
        self.asset_2_reserves = None
        self.issued_pool_tokens = None
        self.asset_1_protocol_fees = None
        self.asset_2_protocol_fees = None
        self.total_fee_share = None
        self.protocol_fee_ratio = None
        self.last_refreshed_round = None

        if fetch:
            self.refresh()
        elif info is not None:
            self.update_from_info(info, fetch)

    def __repr__(self):
        return f"Pool {self.asset_1.unit_name}({self.asset_1.id})-{self.asset_2.unit_name}({self.asset_2.id}) {self.address}"

    @classmethod
    def from_account_info(
        cls,
        account_info: dict,
        client: TinymanV2Client,
        fetch: bool = False,
    ):
        state = get_pool_state_from_account_info(account_info)
        validator_app_id = get_validator_app_id_from_account_info(account_info)
        assert validator_app_id == client.validator_app_id

        info = generate_pool_info(
            address=account_info["address"],
            validator_app_id=client.validator_app_id,
            round_number=account_info["round"],
            state=state,
        )

        pool = Pool(
            client=client,
            asset_a=info["asset_1_id"],
            asset_b=info["asset_2_id"],
            info=info,
            fetch=fetch,
            validator_app_id=info["validator_app_id"],
        )
        return pool

    @classmethod
    def from_state(
        cls,
        address: str,
        state: dict,
        round_number: int,
        client: TinymanV2Client,
        fetch: bool = False,
    ):
        assert state

        info = generate_pool_info(
            address=address,
            validator_app_id=client.validator_app_id,
            round_number=round_number,
            state=state,
        )

        pool = Pool(
            client=client,
            asset_a=info["asset_1_id"],
            asset_b=info["asset_2_id"],
            info=info,
            fetch=fetch,
            validator_app_id=info["validator_app_id"],
        )
        return pool

    def refresh(self, info: Optional[dict] = None) -> None:
        if info is None:
            info = get_pool_info(
                self.client.algod,
                self.validator_app_id,
                self.asset_1.id,
                self.asset_2.id,
            )
        self.update_from_info(info)

    def update_from_info(self, info: dict, fetch: bool = True) -> None:
        if info.get("pool_token_asset_id"):
            self.exists = True
            if fetch:
                self.pool_token_asset = self.client.fetch_asset(
                    info["pool_token_asset_id"]
                )
            else:
                self.pool_token_asset = Asset(
                    id=info["pool_token_asset_id"], unit_name="TMPOOL2", decimals=6
                )

            self.asset_1_reserves = info["asset_1_reserves"]
            self.asset_2_reserves = info["asset_2_reserves"]
            self.issued_pool_tokens = info["issued_pool_tokens"]
            self.asset_1_protocol_fees = info["asset_1_protocol_fees"]
            self.asset_2_protocol_fees = info["asset_2_protocol_fees"]
            self.total_fee_share = info["total_fee_share"]
            self.protocol_fee_ratio = info["protocol_fee_ratio"]
            self.last_refreshed_round = info["round"]

    def get_logicsig(self) -> LogicSigAccount:
        pool_logicsig = get_pool_logicsig(
            self.validator_app_id, self.asset_1.id, self.asset_2.id
        )
        return pool_logicsig

    @property
    def address(self) -> str:
        logicsig = self.get_logicsig()
        pool_address = logicsig.address()
        return pool_address

    @property
    def asset_1_price(self) -> float:
        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        return self.asset_2_reserves / self.asset_1_reserves

    @property
    def asset_2_price(self) -> float:
        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        return self.asset_1_reserves / self.asset_2_reserves

    def info(self) -> dict:
        if not self.exists:
            raise BootstrapIsRequired()

        pool = {
            "address": self.address,
            "asset_1_id": self.asset_1.id,
            "asset_2_id": self.asset_2.id,
            "asset_1_unit_name": self.asset_1.unit_name,
            "asset_2_unit_name": self.asset_2.unit_name,
            "pool_token_asset_id": self.pool_token_asset.id,
            "pool_token_asset_name": self.pool_token_asset.name,
            "asset_1_reserves": self.asset_1_reserves,
            "asset_2_reserves": self.asset_2_reserves,
            "issued_pool_tokens": self.issued_pool_tokens,
            "asset_1_protocol_fees": self.asset_1_protocol_fees,
            "asset_2_protocol_fees": self.asset_2_protocol_fees,
            "total_fee_share": self.total_fee_share,
            "protocol_fee_ratio": self.protocol_fee_ratio,
            "last_refreshed_round": self.last_refreshed_round,
        }
        return pool

    def convert(self, amount: AssetAmount) -> AssetAmount:
        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        if amount.asset == self.asset_1:
            return AssetAmount(self.asset_2, int(amount.amount * self.asset_1_price))
        elif amount.asset == self.asset_2:
            return AssetAmount(self.asset_1, int(amount.amount * self.asset_2_price))

        raise NotImplementedError()

    def prepare_pool_token_asset_optin_transactions(
        self,
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_asset_optin_transactions(
            asset_id=self.pool_token_asset.id,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def fetch_pool_position(self, user_address: Optional[str] = None) -> dict:
        user_address = user_address or self.client.user_address
        account_info = self.client.algod.account_info(user_address)
        assets = {a["asset-id"]: a for a in account_info["assets"]}
        pool_token_asset_amount = assets.get(self.pool_token_asset.id, {}).get(
            "amount", 0
        )
        quote = self.fetch_remove_liquidity_quote(pool_token_asset_amount)
        return {
            self.asset_1: quote.amounts_out[self.asset_1],
            self.asset_2: quote.amounts_out[self.asset_2],
            self.pool_token_asset: quote.pool_token_asset_amount,
            "share": (pool_token_asset_amount / self.issued_pool_tokens),
        }

    def prepare_bootstrap_transactions(
        self,
        user_address: Optional[str] = None,
        pool_algo_balance=None,
        refresh: bool = True,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:

        user_address = user_address or self.client.user_address

        if refresh:
            self.refresh()

        if self.exists:
            raise AlreadyBootstrapped()

        if pool_algo_balance is None:
            pool_account_info = self.client.algod.account_info(self.address)
            pool_algo_balance = pool_account_info["amount"]

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        if self.asset_2.id == 0:
            pool_minimum_balance = MIN_POOL_BALANCE_ASA_ALGO_PAIR
            inner_transaction_count = 5
        else:
            pool_minimum_balance = MIN_POOL_BALANCE_ASA_ASA_PAIR
            inner_transaction_count = 6

        app_call_fee = (inner_transaction_count + 1) * suggested_params.min_fee
        required_algo = pool_minimum_balance + app_call_fee
        # to fund minimum balance increase because of asset creation
        required_algo += 100_000
        required_algo = max(required_algo - pool_algo_balance, 0)

        txn_group = prepare_bootstrap_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            sender=user_address,
            suggested_params=suggested_params,
            app_call_fee=app_call_fee,
            required_algo=required_algo,
        )
        return txn_group

    def fetch_flexible_add_liquidity_quote(
        self,
        amount_a: AssetAmount,
        amount_b: AssetAmount,
        slippage: float = 0.05,
        refresh: bool = True,
    ) -> FlexibleAddLiquidityQuote:
        assert {self.asset_1, self.asset_2} == {
            amount_a.asset,
            amount_b.asset,
        }, "Pool assets and given assets don't match."

        amount_1 = amount_a if amount_a.asset == self.asset_1 else amount_b
        amount_2 = amount_a if amount_a.asset == self.asset_2 else amount_b

        if refresh:
            self.refresh()

        if not self.exists:
            raise BootstrapIsRequired()

        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        (
            pool_token_asset_amount,
            swap_from_asset_1_to_asset_2,
            swap_in_amount,
            swap_out_amount,
            swap_total_fee_amount,
            swap_price_impact,
        ) = calculate_subsequent_add_liquidity(
            asset_1_reserves=self.asset_1_reserves,
            asset_2_reserves=self.asset_2_reserves,
            issued_pool_tokens=self.issued_pool_tokens,
            total_fee_share=self.total_fee_share,
            asset_1_amount=amount_1.amount,
            asset_2_amount=amount_2.amount,
        )

        internal_swap_quote = InternalSwapQuote(
            amount_in=AssetAmount(
                self.asset_1 if swap_from_asset_1_to_asset_2 else self.asset_2,
                swap_in_amount,
            ),
            amount_out=AssetAmount(
                self.asset_2 if swap_from_asset_1_to_asset_2 else self.asset_1,
                swap_out_amount,
            ),
            swap_fees=AssetAmount(
                self.asset_1 if swap_from_asset_1_to_asset_2 else self.asset_2,
                swap_total_fee_amount,
            ),
            price_impact=swap_price_impact,
        )

        quote = FlexibleAddLiquidityQuote(
            amounts_in={
                self.asset_1: amount_1,
                self.asset_2: amount_2,
            },
            pool_token_asset_amount=AssetAmount(
                self.pool_token_asset, pool_token_asset_amount
            ),
            slippage=slippage,
            internal_swap_quote=internal_swap_quote,
        )
        return quote

    def fetch_single_asset_add_liquidity_quote(
        self, amount_a: AssetAmount, slippage: float = 0.05, refresh: bool = True
    ) -> SingleAssetAddLiquidityQuote:
        if refresh:
            self.refresh()

        if not self.exists:
            raise BootstrapIsRequired()

        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        if amount_a.asset == self.asset_1:
            (
                pool_token_asset_amount,
                swap_from_asset_1_to_asset_2,
                swap_in_amount,
                swap_out_amount,
                swap_total_fee_amount,
                swap_price_impact,
            ) = calculate_subsequent_add_liquidity(
                asset_1_reserves=self.asset_1_reserves,
                asset_2_reserves=self.asset_2_reserves,
                issued_pool_tokens=self.issued_pool_tokens,
                total_fee_share=self.total_fee_share,
                asset_1_amount=amount_a.amount,
                asset_2_amount=0,
            )
        elif amount_a.asset == self.asset_2:
            (
                pool_token_asset_amount,
                swap_from_asset_1_to_asset_2,
                swap_in_amount,
                swap_out_amount,
                swap_total_fee_amount,
                swap_price_impact,
            ) = calculate_subsequent_add_liquidity(
                asset_1_reserves=self.asset_1_reserves,
                asset_2_reserves=self.asset_2_reserves,
                issued_pool_tokens=self.issued_pool_tokens,
                total_fee_share=self.total_fee_share,
                asset_1_amount=0,
                asset_2_amount=amount_a.amount,
            )
        else:
            assert False, "Given asset doesn't belong to the pool assets."

        internal_swap_quote = InternalSwapQuote(
            amount_in=AssetAmount(
                self.asset_1 if swap_from_asset_1_to_asset_2 else self.asset_2,
                swap_in_amount,
            ),
            amount_out=AssetAmount(
                self.asset_2 if swap_from_asset_1_to_asset_2 else self.asset_1,
                swap_out_amount,
            ),
            swap_fees=AssetAmount(
                self.asset_1 if swap_from_asset_1_to_asset_2 else self.asset_2,
                swap_total_fee_amount,
            ),
            price_impact=swap_price_impact,
        )
        quote = SingleAssetAddLiquidityQuote(
            amount_in=amount_a,
            pool_token_asset_amount=AssetAmount(
                self.pool_token_asset, pool_token_asset_amount
            ),
            slippage=slippage,
            internal_swap_quote=internal_swap_quote,
        )
        return quote

    def fetch_initial_add_liquidity_quote(
        self,
        amount_a: AssetAmount,
        amount_b: AssetAmount,
        refresh: bool = True,
    ) -> InitialAddLiquidityQuote:
        assert {self.asset_1, self.asset_2} == {
            amount_a.asset,
            amount_b.asset,
        }, "Pool assets and given assets don't match."

        amount_1 = amount_a if amount_a.asset == self.asset_1 else amount_b
        amount_2 = amount_a if amount_a.asset == self.asset_2 else amount_b

        if refresh:
            self.refresh()

        if not self.exists:
            raise BootstrapIsRequired()

        if self.issued_pool_tokens:
            raise PoolAlreadyHasLiquidity()

        pool_token_asset_amount = calculate_initial_add_liquidity(
            asset_1_amount=amount_1.amount, asset_2_amount=amount_2.amount
        )
        quote = InitialAddLiquidityQuote(
            amounts_in={
                self.asset_1: amount_1,
                self.asset_2: amount_2,
            },
            pool_token_asset_amount=AssetAmount(
                self.pool_token_asset, pool_token_asset_amount
            ),
        )
        return quote

    def prepare_flexible_add_liquidity_transactions(
        self,
        amounts_in: "dict[Asset, AssetAmount]",
        min_pool_token_asset_amount: int,
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address
        asset_1_amount = amounts_in[self.asset_1]
        asset_2_amount = amounts_in[self.asset_2]

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_flexible_add_liquidity_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            pool_token_asset_id=self.pool_token_asset.id,
            asset_1_amount=asset_1_amount.amount,
            asset_2_amount=asset_2_amount.amount,
            min_pool_token_asset_amount=min_pool_token_asset_amount,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_single_asset_add_liquidity_transactions(
        self,
        amount_in: AssetAmount,
        min_pool_token_asset_amount: Optional[int],
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_single_asset_add_liquidity_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            pool_token_asset_id=self.pool_token_asset.id,
            asset_1_amount=amount_in.amount
            if amount_in.asset == self.asset_1
            else None,
            asset_2_amount=amount_in.amount
            if amount_in.asset == self.asset_2
            else None,
            min_pool_token_asset_amount=min_pool_token_asset_amount,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_initial_add_liquidity_transactions(
        self,
        amounts_in: "dict[Asset, AssetAmount]",
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address
        asset_1_amount = amounts_in[self.asset_1]
        asset_2_amount = amounts_in[self.asset_2]

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_initial_add_liquidity_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            pool_token_asset_id=self.pool_token_asset.id,
            asset_1_amount=asset_1_amount.amount,
            asset_2_amount=asset_2_amount.amount,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_add_liquidity_transactions_from_quote(
        self,
        quote: [
            FlexibleAddLiquidityQuote,
            SingleAssetAddLiquidityQuote,
            InitialAddLiquidityQuote,
        ],
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        if isinstance(quote, FlexibleAddLiquidityQuote):
            return self.prepare_flexible_add_liquidity_transactions(
                amounts_in=quote.amounts_in,
                min_pool_token_asset_amount=quote.min_pool_token_asset_amount_with_slippage,
                user_address=user_address,
                suggested_params=suggested_params,
            )
        elif isinstance(quote, SingleAssetAddLiquidityQuote):
            return self.prepare_single_asset_add_liquidity_transactions(
                amount_in=quote.amount_in,
                min_pool_token_asset_amount=quote.min_pool_token_asset_amount_with_slippage,
                user_address=user_address,
                suggested_params=suggested_params,
            )
        elif isinstance(quote, InitialAddLiquidityQuote):
            return self.prepare_initial_add_liquidity_transactions(
                amounts_in=quote.amounts_in,
                user_address=user_address,
                suggested_params=suggested_params,
            )

        raise Exception(f"Invalid quote type({type(quote)})")

    def fetch_remove_liquidity_quote(
        self,
        pool_token_asset_in: [AssetAmount, int],
        slippage: float = 0.05,
        refresh: bool = True,
    ) -> RemoveLiquidityQuote:
        if not self.exists:
            raise BootstrapIsRequired()

        if isinstance(pool_token_asset_in, int):
            pool_token_asset_in = AssetAmount(
                self.pool_token_asset, pool_token_asset_in
            )

        if refresh:
            self.refresh()

        (
            asset_1_output_amount,
            asset_2_output_amount,
        ) = calculate_remove_liquidity_output_amounts(
            pool_token_asset_amount=pool_token_asset_in.amount,
            asset_1_reserves=self.asset_1_reserves,
            asset_2_reserves=self.asset_2_reserves,
            issued_pool_tokens=self.issued_pool_tokens,
        )
        quote = RemoveLiquidityQuote(
            amounts_out={
                self.asset_1: AssetAmount(self.asset_1, asset_1_output_amount),
                self.asset_2: AssetAmount(self.asset_2, asset_2_output_amount),
            },
            pool_token_asset_amount=pool_token_asset_in,
            slippage=slippage,
        )
        return quote

    def fetch_single_asset_remove_liquidity_quote(
        self,
        pool_token_asset_in: [AssetAmount, int],
        output_asset: Asset,
        slippage: float = 0.05,
        refresh: bool = True,
    ) -> SingleAssetRemoveLiquidityQuote:
        if not self.exists:
            raise BootstrapIsRequired()

        if isinstance(pool_token_asset_in, int):
            pool_token_asset_in = AssetAmount(
                self.pool_token_asset, pool_token_asset_in
            )

        if refresh:
            self.refresh()

        (
            asset_1_output_amount,
            asset_2_output_amount,
        ) = calculate_remove_liquidity_output_amounts(
            pool_token_asset_amount=pool_token_asset_in.amount,
            asset_1_reserves=self.asset_1_reserves,
            asset_2_reserves=self.asset_2_reserves,
            issued_pool_tokens=self.issued_pool_tokens,
        )

        if output_asset == self.asset_1:
            (
                swap_output_amount,
                total_fee_amount,
                price_impact,
            ) = calculate_fixed_input_swap(
                input_supply=self.asset_2_reserves - asset_2_output_amount,
                output_supply=self.asset_1_reserves - asset_1_output_amount,
                swap_input_amount=asset_2_output_amount,
                total_fee_share=self.total_fee_share,
            )
            internal_swap_quote = InternalSwapQuote(
                amount_in=AssetAmount(self.asset_2, asset_2_output_amount),
                amount_out=AssetAmount(self.asset_1, swap_output_amount),
                swap_fees=AssetAmount(self.asset_2, total_fee_amount),
                price_impact=price_impact,
            )
            quote = SingleAssetRemoveLiquidityQuote(
                amount_out=AssetAmount(
                    self.asset_1, asset_1_output_amount + swap_output_amount
                ),
                pool_token_asset_amount=pool_token_asset_in,
                slippage=slippage,
                internal_swap_quote=internal_swap_quote,
            )
        elif output_asset == self.asset_2:
            (
                swap_output_amount,
                total_fee_amount,
                price_impact,
            ) = calculate_fixed_input_swap(
                input_supply=self.asset_1_reserves - asset_1_output_amount,
                output_supply=self.asset_2_reserves - asset_2_output_amount,
                swap_input_amount=asset_1_output_amount,
                total_fee_share=self.total_fee_share,
            )
            internal_swap_quote = InternalSwapQuote(
                amount_in=AssetAmount(self.asset_1, asset_1_output_amount),
                amount_out=AssetAmount(self.asset_2, swap_output_amount),
                swap_fees=AssetAmount(self.asset_1, total_fee_amount),
                price_impact=price_impact,
            )
            quote = SingleAssetRemoveLiquidityQuote(
                amount_out=AssetAmount(
                    self.asset_2, asset_2_output_amount + swap_output_amount
                ),
                pool_token_asset_amount=pool_token_asset_in,
                slippage=slippage,
                internal_swap_quote=internal_swap_quote,
            )
        else:
            assert False

        return quote

    def prepare_remove_liquidity_transactions(
        self,
        pool_token_asset_amount: [AssetAmount, int],
        amounts_out: "dict[Asset, AssetAmount]",
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        if isinstance(pool_token_asset_amount, int):
            pool_token_asset_amount = AssetAmount(
                self.pool_token_asset, pool_token_asset_amount
            )

        user_address = user_address or self.client.user_address
        asset_1_amount = amounts_out[self.asset_1]
        asset_2_amount = amounts_out[self.asset_2]

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_remove_liquidity_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            pool_token_asset_id=self.pool_token_asset.id,
            min_asset_1_amount=asset_1_amount.amount,
            min_asset_2_amount=asset_2_amount.amount,
            pool_token_asset_amount=pool_token_asset_amount.amount,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_single_asset_remove_liquidity_transactions(
        self,
        pool_token_asset_amount: [AssetAmount, int],
        amount_out: AssetAmount,
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        if isinstance(pool_token_asset_amount, int):
            pool_token_asset_amount = AssetAmount(
                self.pool_token_asset, pool_token_asset_amount
            )

        user_address = user_address or self.client.user_address

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_single_asset_remove_liquidity_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            pool_token_asset_id=self.pool_token_asset.id,
            output_asset_id=amount_out.asset.id,
            min_output_asset_amount=amount_out.amount,
            pool_token_asset_amount=pool_token_asset_amount.amount,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_remove_liquidity_transactions_from_quote(
        self,
        quote: [RemoveLiquidityQuote, SingleAssetRemoveLiquidityQuote],
        user_address: Optional[str] = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        if isinstance(quote, SingleAssetRemoveLiquidityQuote):
            return self.prepare_single_asset_remove_liquidity_transactions(
                pool_token_asset_amount=quote.pool_token_asset_amount,
                amount_out=quote.amount_out_with_slippage,
                user_address=user_address,
                suggested_params=suggested_params,
            )
        elif isinstance(quote, RemoveLiquidityQuote):
            return self.prepare_remove_liquidity_transactions(
                pool_token_asset_amount=quote.pool_token_asset_amount,
                amounts_out={
                    self.asset_1: quote.amounts_out_with_slippage[self.asset_1],
                    self.asset_2: quote.amounts_out_with_slippage[self.asset_2],
                },
                user_address=user_address,
                suggested_params=suggested_params,
            )

        raise NotImplementedError()

    def fetch_fixed_input_swap_quote(
        self, amount_in: AssetAmount, slippage: float = 0.05, refresh: bool = True
    ) -> SwapQuote:
        if refresh:
            self.refresh()

        if not self.exists:
            raise BootstrapIsRequired()

        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        if amount_in.asset == self.asset_1:
            asset_out = self.asset_2
            input_supply = self.asset_1_reserves
            output_supply = self.asset_2_reserves
        elif amount_in.asset == self.asset_2:
            asset_out = self.asset_1
            input_supply = self.asset_2_reserves
            output_supply = self.asset_1_reserves
        else:
            assert False

        swap_output_amount, total_fee_amount, price_impact = calculate_fixed_input_swap(
            input_supply=input_supply,
            output_supply=output_supply,
            swap_input_amount=amount_in.amount,
            total_fee_share=self.total_fee_share,
        )
        amount_out = AssetAmount(asset_out, swap_output_amount)

        quote = SwapQuote(
            swap_type="fixed-input",
            amount_in=amount_in,
            amount_out=amount_out,
            swap_fees=AssetAmount(amount_in.asset, total_fee_amount),
            slippage=slippage,
            price_impact=price_impact,
        )
        return quote

    def fetch_fixed_output_swap_quote(
        self, amount_out: AssetAmount, slippage: float = 0.05, refresh: bool = True
    ) -> SwapQuote:
        if refresh:
            self.refresh()

        if not self.exists:
            raise BootstrapIsRequired()

        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        if amount_out.asset == self.asset_1:
            asset_in = self.asset_2
            input_supply = self.asset_2_reserves
            output_supply = self.asset_1_reserves
        elif amount_out.asset == self.asset_2:
            asset_in = self.asset_1
            input_supply = self.asset_1_reserves
            output_supply = self.asset_2_reserves
        else:
            assert False

        swap_input_amount, total_fee_amount, price_impact = calculate_fixed_output_swap(
            input_supply=input_supply,
            output_supply=output_supply,
            swap_output_amount=amount_out.amount,
            total_fee_share=self.total_fee_share,
        )
        amount_in = AssetAmount(asset_in, swap_input_amount)

        quote = SwapQuote(
            swap_type="fixed-output",
            amount_out=amount_out,
            amount_in=amount_in,
            swap_fees=AssetAmount(amount_in.asset, total_fee_amount),
            slippage=slippage,
            price_impact=price_impact,
        )
        return quote

    def prepare_swap_transactions(
        self,
        amount_in: AssetAmount,
        amount_out: AssetAmount,
        swap_type: [str, bytes],
        user_address: str = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_swap_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            asset_in_id=amount_in.asset.id,
            asset_in_amount=amount_in.amount,
            asset_out_amount=amount_out.amount,
            swap_type=swap_type,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_swap_transactions_from_quote(
        self,
        quote: SwapQuote,
        user_address: str = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        return self.prepare_swap_transactions(
            amount_in=quote.amount_in_with_slippage,
            amount_out=quote.amount_out_with_slippage,
            swap_type=quote.swap_type,
            user_address=user_address,
            suggested_params=suggested_params,
        )

    def fetch_flash_loan_quote(
        self,
        loan_amount_a: AssetAmount,
        loan_amount_b: AssetAmount,
        refresh: bool = True,
    ) -> FlashLoanQuote:
        assert {self.asset_1, self.asset_2} == {
            loan_amount_a.asset,
            loan_amount_b.asset,
        }, "Pool assets and given assets don't match."

        if loan_amount_a.asset == self.asset_1:
            loan_amount_1 = loan_amount_a
        else:
            loan_amount_1 = loan_amount_b

        if loan_amount_a.asset == self.asset_2:
            loan_amount_2 = loan_amount_a
        else:
            loan_amount_2 = loan_amount_b

        if refresh:
            self.refresh()

        if not self.exists:
            raise BootstrapIsRequired()

        if not self.issued_pool_tokens:
            raise PoolHasNoLiquidity()

        if loan_amount_1.amount > self.asset_1_reserves:
            raise Exception(
                f"The loan amount({loan_amount_1.amount}) cannot exceed the reserves."
            )

        if loan_amount_2.amount > self.asset_2_reserves:
            raise Exception(
                f"The loan amount({loan_amount_2.amount}) cannot exceed the reserves."
            )

        quote = FlashLoanQuote(
            amounts_out={
                self.asset_1: loan_amount_1,
                self.asset_2: loan_amount_2,
            },
            amounts_in={
                self.asset_1: AssetAmount(
                    self.asset_1,
                    amount=calculate_flash_loan_payment_amount(
                        loan_amount=loan_amount_1.amount,
                        total_fee_share=self.total_fee_share,
                    ),
                ),
                self.asset_2: AssetAmount(
                    self.asset_2,
                    amount=calculate_flash_loan_payment_amount(
                        loan_amount=loan_amount_2.amount,
                        total_fee_share=self.total_fee_share,
                    ),
                ),
            },
            fees={
                self.asset_1: AssetAmount(
                    self.asset_1,
                    amount=calculate_fixed_input_fee_amount(
                        input_amount=loan_amount_1.amount,
                        total_fee_share=self.total_fee_share,
                    ),
                ),
                self.asset_2: AssetAmount(
                    self.asset_2,
                    amount=calculate_fixed_input_fee_amount(
                        input_amount=loan_amount_2.amount,
                        total_fee_share=self.total_fee_share,
                    ),
                ),
            },
        )
        return quote

    def prepare_flash_loan_transactions(
        self,
        amounts_out: "dict[Asset, AssetAmount]",
        amounts_in: "dict[Asset, AssetAmount]",
        transactions: "list[Transaction]",
        user_address: str = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        txn_group = prepare_flash_loan_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            asset_1_loan_amount=amounts_out[self.asset_1].amount,
            asset_2_loan_amount=amounts_out[self.asset_2].amount,
            asset_1_payment_amount=amounts_in[self.asset_1].amount,
            asset_2_payment_amount=amounts_in[self.asset_2].amount,
            transactions=transactions,
            sender=user_address,
            suggested_params=suggested_params,
        )
        return txn_group

    def prepare_flash_loan_transactions_from_quote(
        self,
        quote: FlashLoanQuote,
        transactions: "list[Transaction]",
        user_address: str = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        return self.prepare_flash_loan_transactions(
            amounts_out=quote.amounts_out,
            amounts_in=quote.amounts_in,
            transactions=transactions,
            user_address=user_address,
            suggested_params=suggested_params,
        )

    def prepare_claim_fees_transactions(
        self,
        fee_collector: str,
        user_address: str = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        return prepare_claim_fees_transactions(
            validator_app_id=self.validator_app_id,
            asset_1_id=self.asset_1.id,
            asset_2_id=self.asset_2.id,
            pool_address=self.address,
            fee_collector=fee_collector,
            sender=user_address,
            suggested_params=suggested_params,
        )

    def prepare_set_fee_transactions(
        self,
        total_fee_share: int,
        protocol_fee_ratio: int,
        user_address: str = None,
        suggested_params: SuggestedParams = None,
    ) -> TransactionGroup:
        user_address = user_address or self.client.user_address

        if suggested_params is None:
            suggested_params = self.client.algod.suggested_params()

        return prepare_set_fee_transactions(
            validator_app_id=self.validator_app_id,
            pool_address=self.address,
            total_fee_share=total_fee_share,
            protocol_fee_ratio=protocol_fee_ratio,
            fee_manager=user_address,
            suggested_params=suggested_params,
        )
