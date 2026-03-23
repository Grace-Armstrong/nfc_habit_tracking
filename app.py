from flask import Flask, request, redirect
import csv
from datetime import datetime, timedelta
import os
import json
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web environments
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from collections import Counter

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
    
    # Get event configuration
    events_config = {}
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE) as f:
            events_config = json.load(f)
    
    # Show days since last tracked for non-numeric events
    non_numeric_events = {e: config for e, config in events_config.items() if not config.get("numeric", False)}
    if non_numeric_events:
        html += "<h3>Days Since Last Tracked:</h3>"
        now = datetime.now()
        for event_name in non_numeric_events:
            # Find last occurrence of this event
            last_date = None
            for row in reversed(rows):
                if row[1] == event_name:
                    try:
                        last_date = datetime.fromisoformat(row[0])
                        break
                    except ValueError:
                        pass
            
            # Calculate streak (consecutive days from today going backwards)
            streak = 0
            if last_date:
                # Convert to date (ignore time)
                last_date_only = last_date.date()
                current_date = now.date()
                
                # Check how many consecutive days back the event was tracked
                check_date = current_date
                for row in reversed(rows):
                    if row[1] == event_name:
                        try:
                            row_date = datetime.fromisoformat(row[0]).date()
                            # If this row is for the check_date, increment streak and move back a day
                            if row_date == check_date:
                                streak += 1
                                check_date = check_date - timedelta(days=1)
                            elif row_date < check_date:
                                # Gap found, streak is broken
                                break
                        except ValueError:
                            pass
                
                # Format last tracked
                days_ago = (current_date - last_date_only).days
                if days_ago == 0:
                    last_tracked = "Today"
                elif days_ago == 1:
                    last_tracked = "Yesterday"
                else:
                    last_tracked = f"{days_ago} days ago"
                
                html += f"<p>{event_name}: <strong>{last_tracked}</strong> | Streak: <strong>{streak}</strong> days</p>"
            else:
                html += f"<p>{event_name}: <strong>Never</strong> | Streak: <strong>0</strong> days</p>"
        html += "<br>"
    
    # Add links to daily averages for numeric events
    numeric_events = [e for e, config in events_config.items() if config.get("numeric", False)]
    if numeric_events:
        html += "<h3>Daily Averages:</h3>"
        for event in numeric_events:
            html += f"<a href='/stats?event={event}'>📈 {event}</a><br>"
        html += "<br>"

    html += "<h3>All Logs:</h3>"
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

@app.route("/stats")
def stats():
    """Display daily averages for numeric events only"""
    event_name = request.args.get("event")
    
    # If no event specified, redirect to home
    if not event_name:
        return redirect("/")
    
    # Read CSV data
    rows = []
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)
    
    # Check if event is numeric
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE) as f:
            events_config = json.load(f)
            is_numeric = events_config.get(event_name, {}).get("numeric", False)
    else:
        is_numeric = False
    
    if not is_numeric:
        return redirect("/")
    
    # Filter events from the past 7 days
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    # Get entries for this event from past 7 days
    daily_data = {}
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    # Initialize with last 7 days
    for i in range(7):
        day = now - timedelta(days=(6-i))
        day_key = day.strftime('%Y-%m-%d')
        daily_data[day_key] = {'sum': 0, 'count': 0, 'day_name': day_names[day.weekday()]}
    
    # Populate with data
    for row in rows:
        try:
            timestamp = datetime.fromisoformat(row[0])
            if timestamp >= week_ago and row[1] == event_name:
                day_key = timestamp.strftime('%Y-%m-%d')
                if day_key in daily_data:
                    value = float(row[2]) if row[2] else 0
                    daily_data[day_key]['sum'] += value
                    daily_data[day_key]['count'] += 1
        except (ValueError, IndexError):
            pass
    
    # Calculate averages
    days = []
    averages = []
    for day_key in sorted(daily_data.keys()):
        data = daily_data[day_key]
        avg = data['sum'] / data['count'] if data['count'] > 0 else 0
        days.append(data['day_name'])
        averages.append(avg)
    
    # Create bar graph
    plt.figure(figsize=(10, 6))
    plt.bar(days, averages, color='steelblue')
    plt.xlabel('Day of Week', fontsize=12)
    plt.ylabel('Average Value', fontsize=12)
    plt.title(f'Daily Average - {event_name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # Convert plot to base64 image
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()
    
    # Return HTML with embedded image
    html = f"""
    <h1>Daily Average</h1>
    <img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;">
    <br><br>
    <a href="/">Back to logs</a>
    """
    
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)