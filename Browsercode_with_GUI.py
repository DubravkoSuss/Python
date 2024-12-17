import sqlite3
import psutil
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

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
        time.sleep(0.1)  # Wait to ensure database is unlocked

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

def monitor_browsers(update_table_callback):
    """
    Monitor browsers and send their browsing history to the GUI when closed.
    """
    browser_status = {browser: {'start_time': None, 'end_time': None} for browser in supported_browsers}

    try:
        while True:
            # Get the list of currently running browsers
            running_browsers = {proc.info['name']: proc.create_time()
                                for proc in psutil.process_iter(attrs=['name', 'create_time'])
                                if proc.info['name'] in supported_browsers}

            # Detect browser start
            for browser in running_browsers:
                if browser_status[browser]['start_time'] is None:
                    browser_status[browser]['start_time'] = datetime.fromtimestamp(running_browsers[browser])

            # Detect browser close and fetch history
            for browser, status in browser_status.items():
                if browser not in running_browsers and status['start_time'] is not None and status['end_time'] is None:
                    # Mark browser as closed
                    status['end_time'] = datetime.now()

                    # Fetch browsing history
                    history = fetch_browsing_history(browser, status['start_time'], status['end_time'])

                    # Update the table in GUI
                    update_table_callback(browser, status['start_time'], status['end_time'], history)

                    # Reset browser status
                    browser_status[browser] = {'start_time': None, 'end_time': None}

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

def start_monitoring_thread(update_table_callback):
    """
    Start a thread to monitor browsers.
    """
    import threading
    thread = threading.Thread(target=monitor_browsers, args=(update_table_callback,), daemon=True)
    thread.start()

# GUI
class BrowserHistoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Browser History Monitor")
        self.root.geometry("900x500")
        self.root.bind("<Control-a>", self.select_all)

        # Create frame for Treeview and scrollbar
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Create Treeview for displaying browsing history
        self.tree = ttk.Treeview(frame, columns=("Browser", "Start Time", "End Time", "URL", "Title"), show='headings')
        self.tree.heading("Browser", text="Browser")
        self.tree.heading("Start Time", text="Start Time")
        self.tree.heading("End Time", text="End Time")
        self.tree.heading("URL", text="URL")
        self.tree.heading("Title", text="Title")

        self.tree.column("Browser", width=100)
        self.tree.column("Start Time", width=150)
        self.tree.column("End Time", width=150)
        self.tree.column("URL", width=300)
        self.tree.column("Title", width=200)

        # Add vertical scrollbar
        v_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Pack Treeview widget
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Create delete button
        delete_button = tk.Button(self.root, text="Delete Selected", command=self.delete_selected)
        delete_button.pack(pady=10)

        # Start monitoring browsers
        start_monitoring_thread(self.update_table)

    def update_table(self, browser, start_time, end_time, history):
        """
        Update the Treeview with new browsing history.
        """
        for entry in history:
            url, title = entry[0], entry[1]
            self.tree.insert("", tk.END, values=(browser, start_time, end_time, url, title))

    def delete_selected(self):
        """
        Delete selected rows from the Treeview.
        """
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected to delete.")
            return

        for item in selected_items:
            self.tree.delete(item)

    def select_all(self, event=None):
        """
        Select all rows in the Treeview when Ctrl+A is pressed.
        """
        # Clear any previous selections
        self.tree.selection_remove(self.tree.selection())

        # Select all rows
        for item in self.tree.get_children():
            self.tree.selection_add(item)

        # Prevent default behavior of Ctrl+A in the GUI (e.g., highlighting text)
        return "break"

class BrowserMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Browser Monitor")

        # Create a Treeview widget (table)
        self.tree = ttk.Treeview(root, columns=("Browser", "Status"), show="headings", height=5)
        self.tree.heading("Browser", text="Browser")
        self.tree.heading("Status", text="Status")

        # Add browsers to the table with initial status
        for browser in supported_browsers:
            self.tree.insert("", "end", values=(browser.capitalize(), "Checking..."))

        self.tree.pack(pady=20)

        # Start the monitoring in the background
        self.monitor_browsers()

    def is_browser_running(self):
        """Check if any of the listed browsers are running."""
        running_browsers = []
        for process in psutil.process_iter(['pid', 'name']):
            for browser in supported_browsers:
                if browser in process.info['name'].lower():
                    running_browsers.append(browser)
        return running_browsers

    def monitor_browsers(self):
        """Check browsers and update the table accordingly."""
        current_browsers = self.is_browser_running()

        # Update the table with the current status of each browser
        for i, browser in enumerate(supported_browsers):
            status = "Running" if browser in current_browsers else "Not Running"
            self.tree.item(self.tree.get_children()[i], values=(browser.capitalize(), status))

        # Re-run the monitor every 1 second
        self.root.after(1000, self.monitor_browsers)

# Create and run the Tkinter GUI
if __name__ == "__main__":
    root = tk.Tk()
    gui = BrowserHistoryApp(root)
    app = BrowserMonitorApp(root)
    root.mainloop()
