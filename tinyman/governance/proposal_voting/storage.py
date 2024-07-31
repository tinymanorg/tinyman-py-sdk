import time
from dataclasses import dataclass
from typing import Optional
from algosdk.encoding import decode_address, encode_address

from tinyman.governance.proposal_voting.constants import PROPOSAL_BOX_PREFIX, ATTENDANCE_SHEET_BOX_PREFIX, PROPOSAL_STATE_CANCELLED, PROPOSAL_STATE_EXECUTED, PROPOSAL_STATE_WAITING_FOR_APPROVAL, PROPOSAL_STATE_PENDING, PROPOSAL_STATE_ACTIVE, PROPOSAL_STATE_DEFEATED, PROPOSAL_STATE_SUCCEEDED
from tinyman.governance.utils import get_raw_box_value
from tinyman.utils import int_to_bytes, bytes_to_int


@dataclass
class ProposalVotingAppGlobalState:
    vault_app_id: int
    proposal_index_counter: int
    voting_delay: int
    voting_duration: int
    proposal_threshold: int
    proposal_threshold_numerator: int
    quorum_threshold: int
    approval_requirement: int
    manager: str
    proposal_manager: str


@dataclass
class Proposal:
    index: int
    creation_timestamp: int
    voting_start_timestamp: int
    voting_end_timestamp: int
    snapshot_total_voting_power: int
    vote_count: int
    quorum_threshold: int
    against_voting_power: int
    for_voting_power: int
    abstain_voting_power: int
    is_approved: bool
    is_cancelled: bool
    is_executed: bool
    is_quorum_reached: bool
    proposer_address: str
    execution_hash: str
    executor_address: str

    @property
    def snapshot_timestamp(self) -> int:
        return self.creation_timestamp

    @property
    def is_vote_succeeded(self) -> bool:
        return self.for_voting_power > self.against_voting_power

    @property
    def state(self):
        now = int(time.time())

        if self.is_cancelled:
            return PROPOSAL_STATE_CANCELLED
        elif self.is_executed:
            return PROPOSAL_STATE_EXECUTED
        elif not self.voting_start_timestamp:
            return PROPOSAL_STATE_WAITING_FOR_APPROVAL
        elif now < self.voting_start_timestamp:
            return PROPOSAL_STATE_PENDING
        elif now < self.voting_end_timestamp:
            return PROPOSAL_STATE_ACTIVE
        elif not self.is_quorum_reached or not self.is_vote_succeeded:
            return PROPOSAL_STATE_DEFEATED
        else:
            return PROPOSAL_STATE_SUCCEEDED


def get_proposal_box_name(proposal_id: str) -> bytes:
    return PROPOSAL_BOX_PREFIX + proposal_id.encode()


def get_attendance_sheet_box_name(address: str, box_index: int) -> bytes:
    return ATTENDANCE_SHEET_BOX_PREFIX + decode_address(address) + int_to_bytes(box_index)


def parse_box_proposal(raw_box) -> Proposal:
    proposal = Proposal(
        index=bytes_to_int(raw_box[:8]),
        creation_timestamp=bytes_to_int(raw_box[8:16]),
        voting_start_timestamp=bytes_to_int(raw_box[16:24]),
        voting_end_timestamp=bytes_to_int(raw_box[24:32]),
        snapshot_total_voting_power=bytes_to_int(raw_box[32:40]),
        vote_count=bytes_to_int(raw_box[40:48]),
        quorum_threshold=bytes_to_int(raw_box[48:56]),
        against_voting_power=bytes_to_int(raw_box[56:64]),
        for_voting_power=bytes_to_int(raw_box[64:72]),
        abstain_voting_power=bytes_to_int(raw_box[72:80]),
        is_approved=bool(bytes_to_int(raw_box[80:81])),
        is_cancelled=bool(bytes_to_int(raw_box[81:82])),
        is_executed=bool(bytes_to_int(raw_box[82:83])),
        is_quorum_reached=bool(bytes_to_int(raw_box[83:84])),
        proposer_address=encode_address(raw_box[84:116]),
        execution_hash=raw_box[116:150],
        executor_address=encode_address(raw_box[150:182]),
    )
    return proposal


def get_proposal(algod, app_id: int, proposal_id: str) -> Optional[Proposal]:
    box_name = get_proposal_box_name(proposal_id)
    raw_box = get_raw_box_value(algod, app_id, box_name)
    if not raw_box:
        return None
    return parse_box_proposal(raw_box)
