from typing import Dict, List, Optional, Any


class TealishMap:
    def __init__(self, map: Optional[Dict[str, Any]] = None) -> None:
        self.pc_teal: List[int] = []
        self.teal_tealish: List[int] = [0]
        self.errors: Dict[int, str] = {}
        if map:
            self.from_dict(map)

    def from_dict(self, map):
        self.pc_teal = map.get("pc_teal", [])
        self.teal_tealish = map.get("teal_tealish", [])
        self.errors: Dict[int, str] = {
            int(k): v for k, v in map.get("errors", {}).items()
        }

    def add_teal_line(self, tealish_line):
        self.teal_tealish.append(tealish_line)

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
