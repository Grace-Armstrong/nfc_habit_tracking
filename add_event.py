import json
import sys

BASE_URL = "https://gracearmstrong.pythonanywhere.com/log"

if len(sys.argv) < 2:
    print("Usage: python add_event.py <event_name>")
    sys.exit(1)

event = sys.argv[1]

numeric = input("Is this event numeric? (y/n): ").lower() == "y"

# Make sure events.json exists and is valid JSON
try:
    with open("events.json", "r") as f:
        data = json.load(f)
except json.JSONDecodeError:
    data = {}

data[event] = {"numeric": numeric}

with open("events.json", "w") as f:
    json.dump(data, f, indent=2)

url = f"{BASE_URL}?event={event}"

print("\n✅ Event added!")
print(f"Event: {event}")
print(f"Numeric: {numeric}")
print("\n📲 NFC URL:")
print(url)
