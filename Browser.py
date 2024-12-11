import sqlite3
import psutil
import time
from datetime import datetime, timedelta, timezone

# List of supported browser names
supported_browsers = ['firefox.exe', 'chrome.exe', 'msedge.exe']

# Profile paths for supported browsers
profile_paths = {
    'firefox.exe': r"C:\\Users\\Administrator\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\7592e3y8.default-release\\places.sqlite",
    'chrome.exe':  r"C:\\Users\\Administrator\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History",
    'msedge.exe':  r"C:\\Users\\Administrator\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History"
}

def fetch_browsing_history(browser, start_time, end_time):
    """
    Fetch and display browsing history for a browser session.
    """
    profile_path = profile_paths.get(browser)
    if not profile_path:
        print(f"No profile path configured for {browser}.")
        return

    # Convert start and end times to the appropriate format
    start_microseconds = int(start_time.timestamp() * 1_000_000)
    end_microseconds = int(end_time.timestamp() * 1_000_000)

    try:
        # Wait for 5 seconds to ensure the database is unlocked after the browser is closed
        print(f"Waiting for 5 seconds before accessing {browser}'s history...")
        time.sleep(2)

        # Connect to the browser's history database
        conn = sqlite3.connect(profile_path)
        cursor = conn.cursor()

        if browser == 'firefox.exe':
            # Query for Firefox
            history_query = """
            SELECT url, title, last_visit_date
            FROM moz_places
            WHERE last_visit_date BETWEEN ? AND ?
            ORDER BY last_visit_date ASC
            """
            cursor.execute(history_query, (start_microseconds, end_microseconds))
        else:
            # Query for Chrome and Edge
            # Convert microseconds to WebKit timestamp (microseconds since 1601-01-01)
            # WebKit timestamp is in microseconds since 1601-01-01
            webkit_epoch = datetime(1601, 1, 1)

            one_hour_in_microseconds = 3_600_000_000

            start_webkit = (start_time - webkit_epoch).total_seconds() * 1_000_000  - one_hour_in_microseconds
            end_webkit = (end_time - webkit_epoch).total_seconds() * 1_000_000  - one_hour_in_microseconds

            history_query = """
            SELECT url, title, last_visit_time
            FROM urls
            WHERE last_visit_time BETWEEN ? AND ?
            ORDER BY last_visit_time ASC
            """
            cursor.execute(history_query, (start_webkit, end_webkit))

        # Fetch results
        history = cursor.fetchall()

        # Display results
        if not history:
            print(f"\nNo browsing activity recorded during this session for {browser}.")
        else:
            print(f"\nBrowsing history during this session for {browser}:")
            for row in history:
                url, title, timestamp = row
                if browser == 'firefox.exe':
                    visit_time = datetime.fromtimestamp(timestamp / 1_000_000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # WebKit timestamp to Unix time conversion using timedelta
                    timestamp_seconds = timestamp / 1_000_000  # Convert microseconds to seconds
                    visit_time = webkit_epoch + timedelta(seconds=timestamp_seconds)

                    # Convert to desired format
                    visit_time_str = visit_time.strftime('%Y-%m-%d %H:%M:%S')

                    # Add 1 hour for display purposes only
                    visit_time_plus_one_hour = visit_time + timedelta(hours=1)
                    visit_time_plus_one_hour_str = visit_time_plus_one_hour.strftime('%Y-%m-%d %H:%M:%S')

                print(f"URL: {url}")
                print(f"Title: {title}")
                print(f"Last visited: {visit_time_plus_one_hour_str}")
                print('-' * 80)

        # Close the database connection
        conn.close()
    except sqlite3.Error as e:
        print(f"Error accessing {browser} history database: {e}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")

def monitor_browsers():
    """
    Monitor supported browsers and record their start and stop times.
    """
    # Dictionary to track the status of browsers
    browser_status = {browser: {'start_time': None, 'end_time': None} for browser in supported_browsers}
    # List to store browser activity data
    browser_activity_log = []

    print("Monitoring supported browsers... Press Ctrl+C to stop.")

    try:
        while True:
            # Get the currently running processes
            running_browsers = {proc.info['name']: proc.create_time()
                                for proc in psutil.process_iter(attrs=['name', 'create_time'])
                                if proc.info['name'] in supported_browsers}

            # Detect browser start
            for browser in running_browsers:
                if browser_status[browser]['start_time'] is None:
                    browser_status[browser]['start_time'] = datetime.fromtimestamp(running_browsers[browser])
                    print(f"{browser} started at {browser_status[browser]['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")

            # Detect browser end
            for browser in browser_status:
                if browser not in running_browsers and browser_status[browser]['start_time'] is not None and \
                        browser_status[browser]['end_time'] is None:
                    browser_status[browser]['end_time'] = datetime.now()
                    print(f"{browser} ended at {browser_status[browser]['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")

                    # Log the browser session
                    browser_activity_log.append({
                        'browser': browser,
                        'start_time': browser_status[browser]['start_time'],
                        'end_time': browser_status[browser]['end_time']
                    })

                    # Fetch browsing history for this session
                    fetch_browsing_history(
                        browser,
                        browser_status[browser]['start_time'],
                        browser_status[browser]['end_time']
                    )

                    # Reset the browser status for future tracking
                    browser_status[browser] = {'start_time': None, 'end_time': None}

            time.sleep(1)  # Check every second

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
        return browser_activity_log
# Start monitoring
activity_log = monitor_browsers()

# Display collected data
print("\nCollected Browser Activity Data:")
for entry in activity_log:
    print(f"Browser: {entry['browser']}")
    print(f"Start Time: {entry['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End Time: {entry['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print('-' * 40)
