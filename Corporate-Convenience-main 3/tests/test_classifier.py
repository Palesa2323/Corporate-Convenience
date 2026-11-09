
from backend.classifier import predict_department

test_cases = [
    ("My salary has not been paid.", "Finance"),
    ("There is an error on my payslip.", "Finance"),
    ("I need to apply for annual leave.", "HR"),
    ("I want to apply for maternity leave.", "HR"),
    ("I cannot log in to my company email.", "IT"),
    ("My laptop will not connect to Wi-Fi.", "IT"),
    ("The office air conditioner is broken.", "Operations"),
    ("The office lights are not working.", "Operations"),
]

print("\nCORPORATE CONVENIENCE - CLASSIFIER TESTS\n")

passed = 0

for message, expected in test_cases:
    actual = predict_department(message)

    result = "PASS" if actual == expected else "FAIL"

    if result == "PASS":
        passed += 1

    print(f"Message: {message}")
    print(f"Expected: {expected}")
    print(f"Predicted: {actual}")
    print(f"Result: {result}\n")

print(f"Tests passed: {passed}/{len(test_cases)}")
