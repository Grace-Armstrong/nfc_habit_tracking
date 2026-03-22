from flask import Flask, request, redirect
import csv
from datetime import datetime
import os
import json

app = Flask(__name__)

# Absolute path to your project folder
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Files
FILE = os.path.join(PROJECT_DIR, "data.csv")
EVENTS_FILE = os.path.join(PROJECT_DIR, "events.json")

# Create data.csv if it doesn't exist
if not os.path.exists(FILE):
    with open(FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "event", "value"])

@app.route("/")
def home():
    rows = []
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)

    html = "<h1>Logs</h1>"

    for i, row in enumerate(rows):
        html += f"""
        <p>
            {row[0]} - {row[1]} {row[2] if len(row) > 2 else ""}
            <a href="/delete?index={i}">❌ delete</a>
        </p>
        """

    return html

@app.route("/log")
def log():
    event = request.args.get("event")

    # Make sure events.json exists
    if not os.path.exists(EVENTS_FILE):
        return "No events defined. Please create events.json first."

    with open(os.path.join(PROJECT_DIR, "events.json")) as f:
        events = json.load(f)

    if event not in events:
        return "Invalid event"

    is_numeric = events[event].get("numeric", False)
    value = request.args.get("value")

    # If numeric and no value provided → show input form
    if is_numeric and value is None:
        return f"""
        <h2>Enter value for {event}</h2>
        <form action="/log">
            <input type="hidden" name="event" value="{event}">
            <input type="number" name="value" step="any" required>
            <button type="submit">Submit</button>
        </form>
        """

    # Log the data
    with open(FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), event, value or ""])

    # Get index for undo
    with open(FILE, "r") as f:
        reader = list(csv.reader(f))
        index = len(reader) - 2

    return f"""
    <h2>✅ Logged: {event} {value or ""}</h2>
    <a href="/delete?index={index}">❌ Undo</a><br><br>
    <a href="/">View all logs</a>
    """

@app.route("/delete")
def delete():
    index = int(request.args.get("index"))

    with open(FILE, "r") as f:
        reader = list(csv.reader(f))

    header = reader[0]
    rows = reader[1:]

    if 0 <= index < len(rows):
        rows.pop(index)

    with open(FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)