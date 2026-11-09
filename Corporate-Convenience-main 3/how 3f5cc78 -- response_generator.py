[33mcommit fd3085f77e3533d4e70c17bcd98782c67db14f51[m
Author: Tebogo Rakoto <YOUR_GITHUB_EMAIL>
Date:   Thu Oct 29 10:10:30 2026 +0200

    Add AI response logic and tests

[1mdiff --git a/response_generator.py b/response_generator.py[m
[1mnew file mode 100644[m
[1mindex 0000000..4346295[m
[1m--- /dev/null[m
[1m+++ b/response_generator.py[m
[36m@@ -0,0 +1,88 @@[m
[32m+[m
[32m+[m[32mfrom classifier import predict_department[m
[32m+[m
[32m+[m
[32m+[m[32mURGENT_PHRASES = [[m
[32m+[m[32m    "do not use your laptop",[m
[32m+[m[32m    "don't use your laptop",[m
[32m+[m[32m    "do not use your computer",[m
[32m+[m[32m    "stop using your laptop",[m
[32m+[m[32m    "security warning",[m
[32m+[m[32m    "suspicious activity",[m
[32m+[m[32m    "account compromised",[m
[32m+[m[32m    "possible virus",[m
[32m+[m[32m    "hacked",[m
[32m+[m[32m][m
[32m+[m
[32m+[m
[32m+[m[32mdef detect_priority(message):[m
[32m+[m[32m    text = message.lower()[m
[32m+[m[32m    return ([m
[32m+[m[32m        "Urgent"[m
[32m+[m[32m        if any(phrase in text for phrase in URGENT_PHRASES)[m
[32m+[m[32m        else "Normal"[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m
[32m+[m[32mdef generate_response(message, department, tone="Formal",[m
[32m+[m[32m                      priority="Normal"):[m
[32m+[m[32m    if priority == "Urgent":[m
[32m+[m[32m        return ([m
[32m+[m[32m            "Urgent IT Support Notice: Please follow the instruction "[m
[32m+[m[32m            "not to use your laptop. Do not attempt to troubleshoot "[m
[32m+[m[32m            "or restart it. Contact IT Support through an approved "[m
[32m+[m[32m            "alternative channel. A human support agent should review "[m
[32m+[m[32m            "this case. Did IT Support give you this instruction, "[m
[32m+[m[32m            "or did you see a warning message?"[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    replies = {[m
[32m+[m[32m        "IT": "Thank you for contacting IT Support. Please describe the technical issue.",[m
[32m+[m[32m        "HR": "Thank you for contacting HR. Please explain your employee-related query.",[m
[32m+[m[32m        "Finance": "Thank you for contacting Finance. Please describe your payment or expense query.",[m
[32m+[m[32m        "Operations": "Thank you for contacting Operations. Please describe the workplace issue.",[m
[32m+[m[32m    }[m
[32m+[m
[32m+[m[32m    reply = replies.get([m
[32m+[m[32m        department,[m
[32m+[m[32m        "Thank you for contacting Corporate Convenience. Your request needs review."[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m[32m    if tone == "Friendly":[m
[32m+[m[32m        reply = "Hi! " + reply[m
[32m+[m[32m    elif tone == "Urgent":[m
[32m+[m[32m        reply = "Priority support request: " + reply[m
[32m+[m
[32m+[m[32m    return reply[m
[32m+[m
[32m+[m
[32m+[m[32mdef analyse_message(message, tone="Formal"):[m
[32m+[m[32m    if not isinstance(message, str) or not message.strip():[m
[32m+[m[32m        raise ValueError("Please enter an employee support message.")[m
[32m+[m
[32m+[m[32m    message = message.strip()[m
[32m+[m[32m    department = predict_department(message)[m
[32m+[m[32m    priority = detect_priority(message)[m
[32m+[m
[32m+[m[32m    # Route the known laptop/security phrases to IT for review.[m
[32m+[m[32m    if priority == "Urgent":[m
[32m+[m[32m        department = "IT"[m
[32m+[m
[32m+[m[32m    return {[m
[32m+[m[32m        "employee_message": message,[m
[32m+[m[32m        "predicted_department": department,[m
[32m+[m[32m        "priority": priority,[m
[32m+[m[32m        "tone": tone,[m
[32m+[m[32m        "draft_response": generate_response([m
[32m+[m[32m            message, department, tone, priority[m
[32m+[m[32m        ),[m
[32m+[m[32m        "requires_human_review": priority == "Urgent",[m
[32m+[m[32m    }[m
[32m+[m
[32m+[m
[32m+[m[32mif __name__ == "__main__":[m
[32m+[m[32m    message = input("Enter an employee support message: ")[m
[32m+[m[32m    result = analyse_message(message)[m
[32m+[m
[32m+[m[32m    for key, value in result.items():[m
[32m+[m[32m        print(f"{key}: {value}")[m
