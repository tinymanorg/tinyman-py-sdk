from typing import Dict, Optional, Any


class TealishMap:
    def __init__(self, map: Dict[str, Any]) -> None:
        self.pc_teal = map.get("pc_teal", [])
        self.teal_tealish = map.get("teal_tealish", [])
        self.errors: Dict[int, str] = {
            int(k): v for k, v in map.get("errors", {}).items()
        }

    def get_tealish_line_for_pc(self, pc: int) -> Optional[int]:
        teal_line = self.get_teal_line_for_pc(pc)
        if teal_line is not None:
            return self.get_tealish_line_for_teal(teal_line)
        return None

    def get_teal_line_for_pc(self, pc: int) -> Optional[int]:
        return self.pc_teal[pc]

    def get_tealish_line_for_teal(self, teal_line: int) -> int:
        return self.teal_tealish[teal_line]

    def get_error_for_pc(self, pc: int) -> Optional[str]:
        tealish_line = self.get_tealish_line_for_pc(pc)
        if tealish_line is not None:
            return self.errors.get(tealish_line, None)
        return None
