import json
import importlib.resources
from algosdk.future.transaction import LogicSig
import tinyman.v1.staking
from tinyman.utils import get_program

_contracts = json.loads(importlib.resources.read_text(tinyman.v1.staking, 'asc.json'))

staking_app_def = _contracts['contracts']['staking_app']
