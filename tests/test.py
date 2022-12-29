from base64 import b64encode
from unittest import TestCase

from tinyman.utils import generate_app_call_note, parse_app_call_note


class BaseTestCase(TestCase):
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
        result = parse_app_call_note(b"invalid format")
        self.assertEqual(result, None)
