import unittest

from scripts.convert_topchina_proxy_list import (
    build_clash_config,
    parse_proxy_rows,
    render_clash_yaml,
)


SAMPLE_MARKDOWN = """
| **IP address:port** | **Region** | **Username** |
|---|---|---|
| 1.2.3.4:8081 | US | user-a |
| invalid | US | skipped |
| 5.6.7.8:8081 | JP | user-b |
| 1.2.3.4:8081 | US | duplicate |
"""


class ConvertTopChinaProxyListTest(unittest.TestCase):
    def test_parse_proxy_rows_skips_invalid_and_duplicate_entries(self):
        rows = parse_proxy_rows(SAMPLE_MARKDOWN)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].server, "1.2.3.4")
        self.assertEqual(rows[0].port, 8081)
        self.assertEqual(rows[0].country, "US")
        self.assertEqual(rows[0].username, "user-a")

    def test_rendered_config_contains_http_proxy_auth_and_match_rule(self):
        rows = parse_proxy_rows(SAMPLE_MARKDOWN)
        config = build_clash_config(
            rows,
            password="1",
            test_url="http://example.com/generate_204",
            source_url="https://example.com/source.md",
        )
        rendered = render_clash_yaml(config, source_updated=None)

        self.assertIn('type: "http"', rendered)
        self.assertIn('username: "user-a"', rendered)
        self.assertIn('password: "1"', rendered)
        self.assertIn('"MATCH,TopChina Select"', rendered)


if __name__ == "__main__":
    unittest.main()
