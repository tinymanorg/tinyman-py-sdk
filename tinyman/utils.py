from base64 import b64decode, b64encode


def get_program(definition, variables=None):
    """
    Return a byte array to be used in LogicSig.
    """
    template = definition['program']
    template_bytes = list(b64decode(template))

    offset = 0
    for v in sorted(definition['variables'], key=lambda v: v['index']):
        name = v['name'].split('TMPL_')[-1].lower()
        value = variables[name]
        start = v['index'] - offset
        end = start + v['length']
        value_encoded = encode_value(value, v['type'])
        value_encoded_len = len(value_encoded)
        diff = v['length'] - value_encoded_len
        offset += diff
        template_bytes[start:end] = list(value_encoded)

    return bytes(template_bytes)


def encode_value(value, type):
    if type == 'int':
        return encode_varint(value)
    raise Exception('Unsupported value type %s!' % type)


def encode_varint(number):
    buf = b''
    while True:
        towrite = number & 0x7f
        number >>= 7
        if number:
            buf += bytes([towrite | 0x80])
        else:
            buf += bytes([towrite])
            break
    return buf


def sign_and_submit_transactions(client, transactions, signed_transactions, sender, sender_sk):
    for i, txn in enumerate(transactions):
        if txn.sender == sender:
            signed_transactions[i] = txn.sign(sender_sk)
    
    txid = client.send_transactions(signed_transactions)
    return wait_for_confirmation(client, txid)


def wait_for_confirmation(client, txid):
    """
    Utility function to wait until the transaction is
    confirmed before proceeding.
    """
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        print("Waiting for confirmation")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
    return txinfo


def int_to_bytes(num):
    return num.to_bytes(8, 'big')


def get_state_int(state, key):
    k = b64encode(key.encode()).decode()
    return state.get(k, {'uint': 0})['uint']


def get_state_bytes(state, key):
    k = b64encode(key.encode()).decode()
    return state.get(k, {'bytes': ''})['bytes']
