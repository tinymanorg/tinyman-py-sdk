from dataclasses import dataclass
from typing import Optional

from Cryptodome.Hash import SHA512
from algosdk import abi
from algosdk.abi.base_type import ABI_LENGTH_SIZE


@dataclass
class Event:
    name: str
    args: [abi.Argument]

    @property
    def signature(self):
        arg_string = ",".join(str(arg.type) for arg in self.args)
        event_signature = "{}({})".format(self.name, arg_string)
        return event_signature

    @property
    def selector(self):
        sha_512_256_hash = SHA512.new(truncate="256")
        sha_512_256_hash.update(self.signature.encode("utf-8"))
        selector = sha_512_256_hash.digest()[:4]
        return selector

    def decode(self, log):
        selector, event_data = log[:4], log[4:]
        assert self.selector == selector

        data = {
            "event_name": self.name
        }
        start = 0
        for arg in self.args:
            if arg.type.is_dynamic():
                if isinstance(arg.type, abi.StringType):
                    size = int.from_bytes(event_data[start:start + ABI_LENGTH_SIZE], "big")
                elif isinstance(arg.type, abi.ArrayDynamicType):
                    size = int.from_bytes(event_data[start:start + ABI_LENGTH_SIZE], "big") * arg.type.child_type.byte_len()
                else:
                    raise NotImplementedError()

                end = start + ABI_LENGTH_SIZE + size
            else:
                end = start + arg.type.byte_len()

            value = event_data[start:end]
            if isinstance(arg.type, abi.ArrayStaticType) and isinstance(arg.type.child_type, abi.ByteType):
                data[arg.name] = bytes(arg.type.decode(value))
            else:
                data[arg.name] = arg.type.decode(value)
            start = end
        return data

    def encode(self, parameters: Optional[list] = None):
        log = self.selector
        if parameters is None:
            parameters = []

        assert len(parameters) == len(self.args)
        for parameter, arg in zip(parameters, self.args):
            log += arg.type.encode(parameter)
        return log


def get_event_by_log(log: bytes, events: list[Event]):
    event_selector = log[:4]
    events_filtered = [event for event in events if event.selector == event_selector]
    assert len(events_filtered) == 1
    event = events_filtered[0]
    return event


def decode_logs(logs: list[bytes], events: list[Event]):
    decoded_logs = []

    for log in logs:
        event = get_event_by_log(log, events)
        decoded_logs.append(event.decode(log))

    return decoded_logs
