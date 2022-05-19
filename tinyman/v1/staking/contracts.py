import importlib.resources
import json

import tinyman.v1.staking

_contracts = json.loads(importlib.resources.read_text(tinyman.v1.staking, 'asc.json'))

staking_app_def = _contracts['contracts']['staking_app']
