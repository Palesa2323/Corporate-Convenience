
import unittest
from response_generator import generate_follow_up


class TestFollowUp(unittest.TestCase):

    def test_laptop_follow_up(self):
        previous = "Please do not use your laptop in the meantime."
        reply = generate_follow_up(
            previous,
            "Who must I contact?",
            "IT"
        )

        self.assertIn("IT Support", reply)
        self.assertIn("safety instruction", reply)

    def test_empty_follow_up(self):
        with self.assertRaises(ValueError):
            generate_follow_up(
                "My laptop has a problem",
                "",
                "IT"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
