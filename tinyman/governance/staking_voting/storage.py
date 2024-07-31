from dataclasses import dataclass
from typing import Optional

from algosdk.encoding import decode_address

from tinyman.governance.proposal_voting.storage import get_proposal_box_name
from tinyman.governance.staking_voting.constants import PROPOSAL_BOX_PREFIX, STAKING_VOTE_BOX_PREFIX, STAKING_ATTENDANCE_BOX_PREFIX
from tinyman.governance.utils import check_nth_bit_from_left, get_raw_box_value
from tinyman.utils import int_to_bytes, bytes_to_int


@dataclass
class StakingVotingAppGlobalState:
    vault_app_id: int
    proposal_index_counter: int
    voting_delay: int
    voting_duration: int
    manager: str
    proposal_manager: str


@dataclass
class StakingDistributionProposal:
    index: int
    creation_timestamp: int
    voting_start_timestamp: int
    voting_end_timestamp: int
    voting_power: int
    vote_count: int
    is_cancelled: bool

    @property
    def snapshot_timestamp(self) -> int:
        return self.creation_timestamp


@dataclass
class StakingVotingAttendanceSheet:
    value: bytes

    @property
    def attendance_sheet(self) -> list[bool]:
        return [check_nth_bit_from_left(self.value, index) for index in range(0, (len(self.value) * 8))]

    def is_vote_casted_for_proposal(self, proposal_index) -> bool:
        return check_nth_bit_from_left(self.value, proposal_index)


def get_staking_distribution_proposal_box_name(proposal_id: str) -> bytes:
    return PROPOSAL_BOX_PREFIX + proposal_id.encode()


def get_staking_vote_box_name(proposal_index: int, asset_id: int) -> bytes:
    return STAKING_VOTE_BOX_PREFIX + int_to_bytes(proposal_index) + int_to_bytes(asset_id)


def get_staking_attendance_sheet_box_name(address: str, box_index: int) -> bytes:
    attendance_sheet_box_name = STAKING_ATTENDANCE_BOX_PREFIX + decode_address(address) + int_to_bytes(box_index)
    return attendance_sheet_box_name


def parse_box_staking_distribution_proposal(raw_box) -> StakingDistributionProposal:
    return StakingDistributionProposal(
        index=bytes_to_int(raw_box[:8]),
        creation_timestamp=bytes_to_int(raw_box[8:16]),
        voting_start_timestamp=bytes_to_int(raw_box[16:24]),
        voting_end_timestamp=bytes_to_int(raw_box[24:32]),
        voting_power=bytes_to_int(raw_box[32:40]),
        vote_count=bytes_to_int(raw_box[40:48]),
        is_cancelled=bool(bytes_to_int(raw_box[48:49])),
    )


def get_staking_distribution_proposal(algod, app_id: int, proposal_id: str) -> Optional[StakingDistributionProposal]:
    box_name = get_proposal_box_name(proposal_id)
    raw_box = get_raw_box_value(algod, app_id, box_name)
    if not raw_box:
        return None
    return parse_box_staking_distribution_proposal(raw_box)
