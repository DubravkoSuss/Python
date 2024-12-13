import sqlite3
import psutil
import time
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta, timezone
from threading import Thread

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
    Fetch browsing history for a specific browser and time range.
    """
    profile_path = profile_paths.get(browser)
    if not profile_path:
        return []

    start_microseconds = int(start_time.timestamp() * 1_000_000)
    end_microseconds = int(end_time.timestamp() * 1_000_000)

    history = []

    try:
        time.sleep(2)  # Wait to ensure database is unlocked

        conn = sqlite3.connect(profile_path)
        cursor = conn.cursor()

        if browser == 'firefox.exe':
            history_query = """
            SELECT url, title, last_visit_date
            FROM moz_places
            WHERE last_visit_date BETWEEN ? AND ?
            ORDER BY last_visit_date ASC
            """
            cursor.execute(history_query, (start_microseconds, end_microseconds))
        else:
            webkit_epoch = datetime(1601, 1, 1)
            one_hour_in_microseconds = 3_600_000_000

            start_webkit = (start_time - webkit_epoch).total_seconds() * 1_000_000 - one_hour_in_microseconds
            end_webkit = (end_time - webkit_epoch).total_seconds() * 1_000_000 - one_hour_in_microseconds

            history_query = """
            SELECT url, title, last_visit_time
            FROM urls
            WHERE last_visit_time BETWEEN ? AND ?
            ORDER BY last_visit_time ASC
            """
            cursor.execute(history_query, (start_webkit, end_webkit))

        history = cursor.fetchall()
        conn.close()

    except sqlite3.Error as e:
        print(f"Error accessing {browser} history database: {e}")

    return history

def monitor_browsers(callback):
    """
    Monitor browsers and fetch their activity when they are closed.
    """
    browser_status = {browser: {'start_time': None, 'end_time': None} for browser in supported_browsers}
    browser_activity_log = []




    try:
        while True:
            running_browsers = {proc.info['name']: proc.create_time()
                                for proc in psutil.process_iter(attrs=['name', 'create_time'])
                                if proc.info['name'] in supported_browsers}


            # Detect browser start
            for browser in running_browsers:
                if browser_status[browser]['start_time'] is None:
                    browser_status[browser]['start_time'] = datetime.fromtimestamp(running_browsers[browser])

            # Detect browser end and fetch history
            for browser in browser_status:
                if browser not in running_browsers and browser_status[browser]['start_time'] is not None and \
                        browser_status[browser]['end_time'] is None:
                    browser_status[browser]['end_time'] = datetime.now()

                    # Log the session
                    browser_activity_log.append({
                        'browser': browser,
                        'start_time': browser_status[browser]['start_time'],
                        'end_time': browser_status[browser]['end_time']
                    })

                    # Fetch browsing history
                    history = fetch_browsing_history(
                        browser,
                        browser_status[browser]['start_time'],
                        browser_status[browser]['end_time']
                    )

                    # Send the new data to the GUI
                    callback(browser_activity_log, history)

                    # Reset for next session
                    browser_status[browser] = {'start_time': None, 'end_time': None}

            time.sleep(1)

    except KeyboardInterrupt:
        return browser_activity_log

class BrowserActivityGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Browser Activity Monitor")
        self.root.geometry("800x600")

        self.activity_log = []

        # Setup Treeview for displaying browser activity log
        self.tree = ttk.Treeview(self.root, columns=("Browser", "Start Time", "End Time", "URL", "Title"), show="headings")
        self.tree.heading("Browser", text="Browser")
        self.tree.heading("Start Time", text="Start Time")
        self.tree.heading("End Time", text="End Time")
        self.tree.heading("URL", text="URL")
        self.tree.heading("Title", text="Title")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Button to start monitoring
        self.start_button = tk.Button(self.root, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(pady=10)

        # Button to stop monitoring
        self.stop_button = tk.Button(self.root, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

        # Button to reset the activity log
        self.reset_button = tk.Button(self.root, text="Reset", command=self.reset_activity_log)
        self.reset_button.pack(pady=10)

    def start_monitoring(self):
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Start monitoring in a separate thread
        monitoring_thread = Thread(target=self.monitor_browsers_thread)
        monitoring_thread.daemon = True
        monitoring_thread.start()

    def stop_monitoring(self):
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showinfo("Stopped", "Monitoring has been stopped.")

    def monitor_browsers_thread(self):
        # Start browser monitoring in the background
        monitor_browsers(self.update_activity_log)

    def update_activity_log(self, browser_activity_log, history):
        # Clear the current treeview data
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Add the new data to the treeview
        for entry in browser_activity_log:
            for url, title, timestamp in history:
                visit_time = datetime.fromtimestamp(timestamp / 1_000_000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                self.tree.insert("", "end", values=(
                    entry['browser'],
                    entry['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    entry['end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    url,
                    title
                ))

        messagebox.showinfo("Monitoring Complete", "Browser activity monitoring is complete.")

    def reset_activity_log(self):
        # Clear the Treeview
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Reset the activity log
        self.activity_log = []

        # Re-enable the Start Monitoring button and disable the Stop Monitoring button
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        messagebox.showinfo("Reset", "Activity log has been reset.")


# Create and run the Tkinter GUI
if __name__ == "__main__":
    root = tk.Tk()
    gui = BrowserActivityGUI(root)
    root.mainloop()