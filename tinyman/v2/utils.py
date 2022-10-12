from base64 import b64decode

from tinyman.utils import bytes_to_int


def decode_logs(logs: "list[[bytes, str]]") -> dict:
    decoded_logs = dict()
    for log in logs:
        if type(log) == str:
            log = b64decode(log.encode())
        if b"%i" in log:
            i = log.index(b"%i")
            s = log[0:i].decode()
            value = int.from_bytes(log[i + 2 :], "big")
            decoded_logs[s] = value
        else:
            raise NotImplementedError()
    return decoded_logs


def get_state_from_account_info(account_info, app_id):
    try:
        app = [a for a in account_info["apps-local-state"] if a["id"] == app_id][0]
    except IndexError:
        return {}
    try:
        app_state = {}
        for x in app["key-value"]:
            key = b64decode(x["key"]).decode()
            if x["value"]["type"] == 1:
                value = bytes_to_int(b64decode(x["value"].get("bytes", "")))
            else:
                value = x["value"].get("uint", 0)
            app_state[key] = value
    except KeyError:
        return {}
    return app_state
