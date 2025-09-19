from pathlib import Path
from .struct import register_struct_file, get_struct

SDK_DIR = Path(__file__).parent


register_struct_file(filepath=SDK_DIR / "order_structs.json")
register_struct_file(filepath=SDK_DIR / "registry_structs.json")

AppVersion = get_struct("AppVersion")
Entry = get_struct("Entry")
TriggerOrder = get_struct("TriggerOrder")
RecurringOrder = get_struct("RecurringOrder")
