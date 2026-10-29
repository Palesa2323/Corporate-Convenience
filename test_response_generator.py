
import unittest
from response_generator import analyse_message


class TestResponseGenerator(unittest.TestCase):

    def test_urgent_laptop_message(self):
        result = analyse_message(
            "Please do not use your laptop in the meantime."
        )
        self.assertEqual(result["predicted_department"], "IT")
        self.assertEqual(result["priority"], "Urgent")
        self.assertTrue(result["requires_human_review"])

    def test_tone_control(self):
        message = "I cannot log in to my company email"

        formal = analyse_message(message, tone="Formal")
        friendly = analyse_message(message, tone="Friendly")
        urgent = analyse_message(message, tone="Urgent")

        self.assertNotEqual(
            formal["draft_response"],
            friendly["draft_response"]
        )
        self.assertNotEqual(
            formal["draft_response"],
            urgent["draft_response"]
        )

    def test_empty_message(self):
        with self.assertRaises(ValueError):
            analyse_message("")


if __name__ == "__main__":
    unittest.main(verbosity=2)
