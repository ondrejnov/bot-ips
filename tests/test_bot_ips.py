import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import bot_ips


class BotIpsTests(unittest.TestCase):
    def test_parse_and_deduplicate(self):
        data = {"prefixes": [{"ipv4Prefix": "192.0.2.0/24"},
                             {"ipv6Prefix": "2001:db8::/32"},
                             {"ipv4Prefix": "192.0.2.0/24"}]}
        self.assertEqual([str(n) for n in bot_ips.parse_prefixes(data)],
                         ["192.0.2.0/24", "2001:db8::/32"])

    def test_invalid_payloads(self):
        for data in [None, [], {}, {"prefixes": []}, {"prefixes": [None]},
                     {"prefixes": [{}]}, {"prefixes": [{"ipv4Prefix": "bad"}]},
                     {"prefixes": [{"ipv4Prefix": "2001:db8::/32"}]},
                     {"prefixes": [{"ipv4Prefix": "192.0.2.1/24"}]},
                     {"prefixes": [{"ipv4Prefix": 123}]}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                bot_ips.parse_prefixes(data)

    def test_aggregate_preserves_provenance(self):
        payloads = {
            "https://a.test": {"prefixes": [{"ipv4Prefix": "192.0.2.0/25"}]},
            "https://b.test": {"prefixes": [{"ipv4Prefix": "192.0.2.128/25"},
                                            {"ipv6Prefix": "2001:db8::/32"}]},
        }
        with patch.object(bot_ips, "fetch", side_effect=lambda url, timeout: payloads[url]):
            result = bot_ips.aggregate({"a": "https://a.test", "b": "https://b.test"}, 1)
        self.assertEqual(result["ipv4"], ["192.0.2.0/24"])
        self.assertEqual(result["ipv6"], ["2001:db8::/32"])
        self.assertEqual(result["bots"]["a"]["prefixes"], ["192.0.2.0/25"])
        self.assertIsNone(result["bots"]["a"]["creation_time"])

    def test_failure_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            sources = Path(directory) / "sources.json"
            sources.write_text(json.dumps({"test": "https://example.com/bot.json"}))
            output.write_text("previous snapshot")
            output.with_suffix(".txt").write_text("previous text")
            with patch.object(bot_ips, "fetch", side_effect=TimeoutError("timeout")):
                self.assertEqual(bot_ips.main(["--sources", str(sources), "--output", str(output)]), 1)
            self.assertEqual(output.read_text(), "previous snapshot")
            self.assertEqual(output.with_suffix(".txt").read_text(), "previous text")

    def test_atomic_write_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "snapshot.json"
            old = {"ipv4": ["192.0.2.0/24"], "ipv6": ["2001:db8::/32"]}
            new = {"ipv4": ["198.51.100.0/24"], "ipv6": []}
            bot_ips.write_snapshot(output, old)
            self.assertEqual(output.with_suffix(".txt").read_text(), "192.0.2.0/24\n2001:db8::/32\n")
            with patch.object(bot_ips.os, "replace", side_effect=OSError("failed")):
                with self.assertRaises(OSError):
                    bot_ips.write_snapshot(output, new)
            self.assertEqual(json.loads(output.read_text()), old)
            self.assertEqual(set(Path(directory).iterdir()), {output, output.with_suffix(".txt")})
            bot_ips.write_snapshot(output, new)
            self.assertEqual(json.loads(output.read_text()), new)
            self.assertEqual(output.with_suffix(".txt").read_text(), "198.51.100.0/24\n")

    def test_cli_generates_both_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "custom.json"
            payload = {"prefixes": [{"ipv4Prefix": "192.0.2.0/24"},
                                    {"ipv6Prefix": "2001:db8::/32"}]}
            with patch.object(bot_ips, "fetch", return_value=payload):
                self.assertEqual(bot_ips.main(["--output", str(output)]), 0)
            snapshot = json.loads(output.read_text())
            self.assertEqual(output.with_suffix(".txt").read_text().splitlines(),
                             snapshot["ipv4"] + snapshot["ipv6"])

    def test_reject_overlapping_outputs(self):
        with self.assertRaises(SystemExit) as result:
            bot_ips.main(["--output", "bot-ips.txt"])
        self.assertEqual(result.exception.code, 2)

    def test_retry_policy(self):
        for status, attempts in [(404, 1), (429, 3), (503, 3)]:
            error = HTTPError("https://example.com", status, "error", {}, None)
            with self.subTest(status=status), patch.object(bot_ips, "urlopen", side_effect=error) as request:
                with patch.object(bot_ips.time, "sleep"), self.assertRaises(HTTPError):
                    bot_ips.fetch("https://example.com", 1)
                self.assertEqual(request.call_count, attempts)


if __name__ == "__main__":
    unittest.main()
