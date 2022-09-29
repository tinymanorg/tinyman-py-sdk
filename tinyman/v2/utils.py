from base64 import b64decode


def decode_logs(logs):
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
