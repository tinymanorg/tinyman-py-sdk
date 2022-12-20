from base64 import b64decode


def get_state_from_account_info(account_info, app_id):
    try:
        app = [a for a in account_info["apps-local-state"] if a["id"] == app_id][0]
    except IndexError:
        return {}
    try:
        app_state = {}
        for x in app["key-value"]:
            key = b64decode(x["key"])
            if x["value"]["type"] == 1:
                value = b64decode(x["value"].get("bytes", ""))
            else:
                value = x["value"].get("uint", 0)
            app_state[key] = value
    except KeyError:
        return {}
    return app_state
