from base64 import b64decode, b64encode
from algosdk.future.transaction import LogicSigTransaction, assign_group_id
from algosdk.error import AlgodHTTPError


def get_program(definition, variables=None):
    """
    Return a byte array to be used in LogicSig.
    """
    template = definition['bytecode']
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
    txinfo['txid'] = txid
    print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
    return txinfo


def int_to_bytes(num):
    return num.to_bytes(8, 'big')


def get_state_int(state, key):
    if type(key) == str:
        key = b64encode(key.encode())
    return state.get(key.decode(), {'uint': 0})['uint']


def get_state_bytes(state, key):
    if type(key) == str:
        key = b64encode(key.encode())
    return state.get(key.decode(), {'bytes': ''})['bytes']


class TransactionGroup:

    def __init__(self, transactions):
        transactions = assign_group_id(transactions)
        self.transactions = transactions
        self.signed_transactions = [None for _ in self.transactions]
    
    def sign(self, user):
        user.sign_transaction_group(self)
    
    def sign_with_logicisg(self, logicsig):
        address = logicsig.address()
        for i, txn in enumerate(self.transactions):
            if txn.sender == address:
                self.signed_transactions[i] = LogicSigTransaction(txn, logicsig)

    def sign_with_private_key(self, address, private_key):
        for i, txn in enumerate(self.transactions):
            if txn.sender == address:
                self.signed_transactions[i] = txn.sign(private_key)
    
    def submit(self, algod, wait=False):
        try:
            txid = algod.send_transactions(self.signed_transactions)
        except AlgodHTTPError as e:
            raise Exception(str(e))
        if wait:
            return wait_for_confirmation(algod, txid)
        return {'txid': txid}


