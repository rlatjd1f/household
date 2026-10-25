import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.ledger_tab import parse_amount


class ParseAmountTest(unittest.TestCase):
    def test_accepts_common_formats(self):
        self.assertEqual(parse_amount("12000"), 12000)
        self.assertEqual(parse_amount("12,000"), 12000)
        self.assertEqual(parse_amount(" 3000 "), 3000)
        self.assertEqual(parse_amount("12,000원"), 12000)
        self.assertEqual(parse_amount("₩12,000"), 12000)

    def test_accepts_negative_for_refund(self):
        self.assertEqual(parse_amount("-5000"), -5000)
        self.assertEqual(parse_amount("-5,000원"), -5000)

    def test_rejects_invalid(self):
        for text in ["", "1.5", "만원", "12-000", "--5", "abc"]:
            self.assertIsNone(parse_amount(text), text)


if __name__ == "__main__":
    unittest.main()
