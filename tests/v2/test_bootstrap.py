import unittest

from algosdk.account import generate_account
from algosdk.future.transaction import PaymentTxn, ApplicationOptInTxn
from algosdk.logic import get_application_address

from tests import get_suggested_params
from tinyman.v2.bootstrap import prepare_bootstrap_transactions
from tinyman.v2.constants import BOOTSTRAP_APP_ARGUMENT
from tinyman.v2.contracts import get_pool_logicsig


class BootstrapTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.VALIDATOR_APP_ID = 12345

    def test_asa_asa_pair(self):
        _, sender = generate_account()

        suggested_params = get_suggested_params()
        txn_group = prepare_bootstrap_transactions(
            validator_app_id=self.VALIDATOR_APP_ID,
            asset_1_id=10,
            asset_2_id=8,
            sender=sender,
            app_call_fee=suggested_params.min_fee * 7,
            required_algo=500_000,
            suggested_params=suggested_params,
        )

        transactions = txn_group.transactions
        self.assertEqual(len(transactions), 2)

        self.assertTrue(isinstance(transactions[0], PaymentTxn))
        self.assertEqual(transactions[0].amt, 500_000)
        self.assertEqual(transactions[0].sender, sender)
        self.assertEqual(
            transactions[0].receiver,
            get_pool_logicsig(self.VALIDATOR_APP_ID, 10, 8).address(),
        )
        self.assertEqual(transactions[0].rekey_to, None)

        self.assertTrue(isinstance(transactions[1], ApplicationOptInTxn))
        self.assertEqual(transactions[1].index, self.VALIDATOR_APP_ID)
        self.assertEqual(
            transactions[1].sender,
            get_pool_logicsig(self.VALIDATOR_APP_ID, 10, 8).address(),
        )
        self.assertEqual(transactions[1].fee, suggested_params.min_fee * 7)
        self.assertEqual(transactions[1].app_args, [BOOTSTRAP_APP_ARGUMENT])
        self.assertEqual(transactions[1].foreign_assets, [10, 8])
        self.assertEqual(
            transactions[1].rekey_to, get_application_address(self.VALIDATOR_APP_ID)
        )

    def test_pool_is_already_funded(self):
        _, sender = generate_account()

        suggested_params = get_suggested_params()
        txn_group = prepare_bootstrap_transactions(
            validator_app_id=self.VALIDATOR_APP_ID,
            asset_1_id=10,
            asset_2_id=8,
            sender=sender,
            app_call_fee=suggested_params.min_fee * 6,
            required_algo=0,
            suggested_params=suggested_params,
        )

        transactions = txn_group.transactions
        self.assertEqual(len(transactions), 1)
        self.assertTrue(isinstance(transactions[0], ApplicationOptInTxn))
        self.assertEqual(transactions[0].index, self.VALIDATOR_APP_ID)
        self.assertEqual(
            transactions[0].sender,
            get_pool_logicsig(self.VALIDATOR_APP_ID, 10, 8).address(),
        )
        self.assertEqual(transactions[0].fee, suggested_params.min_fee * 6)
        self.assertEqual(transactions[0].app_args, [BOOTSTRAP_APP_ARGUMENT])
        self.assertEqual(transactions[0].foreign_assets, [10, 8])
        self.assertEqual(
            transactions[0].rekey_to, get_application_address(self.VALIDATOR_APP_ID)
        )
