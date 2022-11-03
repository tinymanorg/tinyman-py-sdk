from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Asset:
    id: int
    name: str = None
    unit_name: str = None
    decimals: int = None

    def __call__(self, amount: int) -> "AssetAmount":
        return AssetAmount(self, amount)

    def __hash__(self) -> int:
        return self.id

    def __repr__(self) -> str:
        return f"Asset({self.unit_name} - {self.id})"

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def fetch(self, algod):
        if self.id > 0:
            params = algod.asset_info(self.id)["params"]
        else:
            params = {
                "name": "Algo",
                "unit-name": "ALGO",
                "decimals": 6,
            }
        self.name = params["name"]
        self.unit_name = params["unit-name"]
        self.decimals = params["decimals"]
        return self


@dataclass
class AssetAmount:
    asset: Asset
    amount: int

    def __mul__(self, other: float):
        if isinstance(other, (float, int)):
            return AssetAmount(self.asset, int(self.amount * other))
        raise TypeError("Unsupported types for *")

    def __add__(self, other: "AssetAmount"):
        if isinstance(other, AssetAmount) and other.asset == self.asset:
            return AssetAmount(self.asset, int(self.amount + other.amount))
        raise TypeError("Unsupported types for +")

    def __sub__(self, other: "AssetAmount"):
        if isinstance(other, AssetAmount) and other.asset == self.asset:
            return AssetAmount(self.asset, int(self.amount - other.amount))
        raise TypeError("Unsupported types for -")

    def __gt__(self, other: "AssetAmount"):
        if isinstance(other, AssetAmount) and other.asset == self.asset:
            return self.amount > other.amount
        if isinstance(other, (float, int)):
            return self.amount > other
        raise TypeError("Unsupported types for >")

    def __lt__(self, other: "AssetAmount"):
        if isinstance(other, AssetAmount) and other.asset == self.asset:
            return self.amount < other.amount
        if isinstance(other, (float, int)):
            return self.amount < other
        raise TypeError("Unsupported types for <")

    def __eq__(self, other: "AssetAmount"):
        if isinstance(other, AssetAmount) and other.asset == self.asset:
            return self.amount == other.amount
        if isinstance(other, (float, int)):
            return self.amount == other
        raise TypeError("Unsupported types for ==")

    def __repr__(self) -> str:
        if self.asset.decimals is not None:
            amount = (
                Decimal(self.amount) / Decimal(10**self.asset.decimals)
            ).quantize(1 / Decimal(10**self.asset.decimals))
            return f"{self.asset.unit_name}('{amount}' Base Unit)"
        else:
            return f"{self.asset.unit_name}('{self.amount}' Micro Unit)"
