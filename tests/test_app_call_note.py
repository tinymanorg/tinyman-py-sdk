from base64 import b64encode
from unittest import TestCase

from algosdk.v2client.algod import AlgodClient

from tinyman.utils import generate_app_call_note, parse_app_call_note
from tinyman.v1.client import TinymanClient, TinymanTestnetClient, TinymanMainnetClient
from tinyman.v1.constants import TESTNET_VALIDATOR_APP_ID_V1_1
from tinyman.v2.client import (
    TinymanV2Client,
    TinymanV2TestnetClient,
    TinymanV2MainnetClient,
)
from tinyman.v2.constants import TESTNET_VALIDATOR_APP_ID_V2


class AppCallNoteTestCase(TestCase):
    maxDiff = None

    def test_app_call_note(self):
        note = generate_app_call_note(
            version="v2", client_name="unit-test", extra_data={"extra": "some text"}
        )
        expected_result = {
            "version": "v2",
            "data": {"extra": "some text", "origin": "unit-test"},
        }

        # test possible versions
        string_note = note
        bytes_note = string_note.encode()
        base64_note = b64encode(bytes_note).decode()

        result = parse_app_call_note(string_note)
        self.assertDictEqual(
            result,
            expected_result,
        )

        result = parse_app_call_note(base64_note)
        self.assertDictEqual(
            result,
            expected_result,
        )

        result = parse_app_call_note(base64_note)
        self.assertDictEqual(
            result,
            expected_result,
        )

        result = parse_app_call_note("invalid format")
        self.assertEqual(result, None)
        result = parse_app_call_note(
            "INVALID+dGlueW1hbi92MjpqeyJvcmlnaW4iOiJ0aW55bWFuLXB5dGhvbi1zZGsifQ=="
        )
        self.assertEqual(result, None)
        result = parse_app_call_note(b"invalid format")
        self.assertEqual(result, None)
        result = parse_app_call_note(
            b'INVALID+tinyman/v2:j{"origin":"tinyman-python-sdk"}'
        )
        self.assertEqual(result, None)

    def test_tinyman_clients(self):
        algod_client = AlgodClient(algod_token="", algod_address="")
        client_name = "test"

        # V1
        self.assertEqual(
            TinymanClient(
                algod_client=algod_client,
                client_name=client_name,
                validator_app_id=TESTNET_VALIDATOR_APP_ID_V1_1,
            ).generate_app_call_note(),
            'tinyman/v1:j{"origin":"test"}',
        )
        self.assertEqual(
            TinymanTestnetClient(
                algod_client=algod_client, client_name=client_name
            ).generate_app_call_note(),
            'tinyman/v1:j{"origin":"test"}',
        )
        self.assertEqual(
            TinymanMainnetClient(
                algod_client=algod_client, client_name=client_name
            ).generate_app_call_note(),
            'tinyman/v1:j{"origin":"test"}',
        )

        # V2
        self.assertEqual(
            TinymanV2Client(
                algod_client=algod_client,
                client_name=client_name,
                validator_app_id=TESTNET_VALIDATOR_APP_ID_V2,
            ).generate_app_call_note(),
            'tinyman/v2:j{"origin":"test"}',
        )
        self.assertEqual(
            TinymanV2TestnetClient(
                algod_client=algod_client, client_name=client_name
            ).generate_app_call_note(),
            'tinyman/v2:j{"origin":"test"}',
        )
        self.assertEqual(
            TinymanV2MainnetClient(
                algod_client=algod_client, client_name=client_name
            ).generate_app_call_note(),
            'tinyman/v2:j{"origin":"test"}',
        )
