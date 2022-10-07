import math
from dataclasses import dataclass

from tinyman.assets import AssetAmount, Asset


@dataclass
class SwapQuote:
    swap_type: str
    amount_in: AssetAmount
    amount_out: AssetAmount
    swap_fees: AssetAmount
    slippage: float
    price_impact: float

    @property
    def amount_out_with_slippage(self) -> AssetAmount:
        if self.swap_type == "fixed-output":
            return self.amount_out

        amount_with_slippage = self.amount_out.amount - int(
            self.amount_out.amount * self.slippage
        )
        return AssetAmount(self.amount_out.asset, amount_with_slippage)

    @property
    def amount_in_with_slippage(self) -> AssetAmount:
        if self.swap_type == "fixed-input":
            return self.amount_in

        amount_with_slippage = self.amount_in.amount + int(
            self.amount_in.amount * self.slippage
        )
        return AssetAmount(self.amount_in.asset, amount_with_slippage)

    @property
    def price(self) -> float:
        return self.amount_out.amount / self.amount_in.amount

    @property
    def price_with_slippage(self) -> float:
        return (
            self.amount_out_with_slippage.amount / self.amount_in_with_slippage.amount
        )


@dataclass
class InternalSwapQuote:
    amount_in: AssetAmount
    amount_out: AssetAmount
    swap_fees: AssetAmount
    price_impact: float

    @property
    def price(self) -> float:
        return self.amount_out.amount / self.amount_in.amount


@dataclass
class FlexibleAddLiquidityQuote:
    amounts_in: dict[Asset, AssetAmount]
    pool_token_asset_amount: AssetAmount
    slippage: float
    internal_swap_quote: InternalSwapQuote = None

    @property
    def min_pool_token_asset_amount_with_slippage(self) -> int:
        return self.pool_token_asset_amount.amount - math.ceil(
            self.pool_token_asset_amount.amount * self.slippage
        )


@dataclass
class SingleAssetAddLiquidityQuote:
    amount_in: AssetAmount
    pool_token_asset_amount: AssetAmount
    slippage: float
    internal_swap_quote: InternalSwapQuote = None

    @property
    def min_pool_token_asset_amount_with_slippage(self) -> int:
        return self.pool_token_asset_amount.amount - math.ceil(
            self.pool_token_asset_amount.amount * self.slippage
        )


@dataclass
class InitialAddLiquidityQuote:
    amounts_in: dict[Asset, AssetAmount]
    pool_token_asset_amount: AssetAmount


@dataclass
class RemoveLiquidityQuote:
    amounts_out: dict[Asset, AssetAmount]
    pool_token_asset_amount: AssetAmount
    slippage: float

    @property
    def amounts_out_with_slippage(self) -> dict[Asset, AssetAmount]:
        amounts_out = {}
        for asset, asset_amount in self.amounts_out.items():
            amount_with_slippage = asset_amount.amount - int(
                (asset_amount.amount * self.slippage)
            )
            amounts_out[asset] = AssetAmount(asset, amount_with_slippage)
        return amounts_out


@dataclass
class SingleAssetRemoveLiquidityQuote:
    amount_out: AssetAmount
    pool_token_asset_amount: AssetAmount
    slippage: float
    internal_swap_quote: InternalSwapQuote = None

    @property
    def amount_out_with_slippage(self) -> AssetAmount:
        amount_with_slippage = self.amount_out.amount - int(
            self.amount_out.amount * self.slippage
        )
        return AssetAmount(self.amount_out.asset, amount_with_slippage)


@dataclass
class FlashLoanQuote:
    amounts_out: dict[Asset, AssetAmount]
    amounts_in: dict[Asset, AssetAmount]
    fees: dict[Asset, AssetAmount]
