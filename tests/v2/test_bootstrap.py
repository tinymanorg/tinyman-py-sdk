from unittest.mock import ANY

from algosdk.account import generate_account
from algosdk.constants import APPCALL_TXN, PAYMENT_TXN
from algosdk.encoding import decode_address
from algosdk.future.transaction import OnComplete
from algosdk.logic import get_application_address

from tests.v2 import BaseTestCase
from tinyman.v2.constants import BOOTSTRAP_APP_ARGUMENT
from tinyman.v2.contracts import get_pool_logicsig
from tinyman.v2.pools import Pool


class BootstrapTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.VALIDATOR_APP_ID = 12345
        cls.application_address = get_application_address(cls.VALIDATOR_APP_ID)

        cls.sender_private_key, cls.user_address = generate_account()
        cls.asset_1_id = 10
        cls.asset_2_id = 8
        cls.pool_address = get_pool_logicsig(
            cls.VALIDATOR_APP_ID, cls.asset_1_id, cls.asset_2_id
        ).address()
        cls.application_address = get_application_address(cls.VALIDATOR_APP_ID)
        cls.pool_state = {}

        cls.pool = Pool(
            client=cls.get_tinyman_client(),
            asset_a=cls.asset_1_id,
            asset_b=cls.asset_2_id,
            info=None,
            fetch=False,
            validator_app_id=cls.VALIDATOR_APP_ID,
        )

    def test_bootstrap(self):
        txn_group = self.pool.prepare_bootstrap_transactions(
            pool_algo_balance=0,
            refresh=False,
            suggested_params=self.get_suggested_params(),
        )

        transactions = txn_group.transactions
        self.assertEqual(len(transactions), 2)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "amt": 1_049_000,
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "rcv": decode_address(self.pool_address),
                "snd": decode_address(self.user_address),
                "type": PAYMENT_TXN,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [BOOTSTRAP_APP_ARGUMENT],
                "apan": OnComplete.OptInOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 7000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "rekey": decode_address(self.application_address),
                "snd": decode_address(self.pool_address),
                "type": APPCALL_TXN,
            },
        )

    def test_pool_is_already_funded(self):
        txn_group = self.pool.prepare_bootstrap_transactions(
            pool_algo_balance=2_000_000,
            refresh=False,
            suggested_params=self.get_suggested_params(),
        )

        transactions = txn_group.transactions
        self.assertEqual(len(transactions), 1)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "apaa": [BOOTSTRAP_APP_ARGUMENT],
                "apan": OnComplete.OptInOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 7000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "rekey": decode_address(self.application_address),
                "snd": decode_address(self.pool_address),
                "type": APPCALL_TXN,
            },
        )


class BootstrapAlgoPoolTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.VALIDATOR_APP_ID = 12345
        cls.application_address = get_application_address(cls.VALIDATOR_APP_ID)

        cls.sender_private_key, cls.user_address = generate_account()
        cls.asset_1_id = 10
        cls.asset_2_id = 0
        cls.pool_address = get_pool_logicsig(
            cls.VALIDATOR_APP_ID, cls.asset_1_id, cls.asset_2_id
        ).address()
        cls.application_address = get_application_address(cls.VALIDATOR_APP_ID)
        cls.pool_state = {}

        cls.pool = Pool(
            client=cls.get_tinyman_client(),
            asset_a=cls.asset_1_id,
            asset_b=cls.asset_2_id,
            info=None,
            fetch=False,
            validator_app_id=cls.VALIDATOR_APP_ID,
        )

    def test_bootstrap(self):
        txn_group = self.pool.prepare_bootstrap_transactions(
            pool_algo_balance=0,
            refresh=False,
            suggested_params=self.get_suggested_params(),
        )

        transactions = txn_group.transactions
        self.assertEqual(len(transactions), 2)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "amt": 948_000,
                "fee": 1000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "rcv": decode_address(self.pool_address),
                "snd": decode_address(self.user_address),
                "type": PAYMENT_TXN,
            },
        )
        self.assertDictEqual(
            dict(transactions[1].dictify()),
            {
                "apaa": [BOOTSTRAP_APP_ARGUMENT],
                "apan": OnComplete.OptInOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 6000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "rekey": decode_address(self.application_address),
                "snd": decode_address(self.pool_address),
                "type": APPCALL_TXN,
            },
        )

    def test_pool_is_already_funded(self):
        txn_group = self.pool.prepare_bootstrap_transactions(
            pool_algo_balance=2_000_000,
            refresh=False,
            suggested_params=self.get_suggested_params(),
        )

        transactions = txn_group.transactions
        self.assertEqual(len(transactions), 1)
        self.assertDictEqual(
            dict(transactions[0].dictify()),
            {
                "apaa": [BOOTSTRAP_APP_ARGUMENT],
                "apan": OnComplete.OptInOC,
                "apas": [self.pool.asset_1.id, self.pool.asset_2.id],
                "apid": self.VALIDATOR_APP_ID,
                "fee": 6000,
                "fv": ANY,
                "gh": ANY,
                "grp": ANY,
                "lv": ANY,
                "rekey": decode_address(self.application_address),
                "snd": decode_address(self.pool_address),
                "type": APPCALL_TXN,
            },
        )
