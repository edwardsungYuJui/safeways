import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass
import queue
import json
import os
import logging


class MonitorStyle:
    # Colors
    BG_COLOR = "#2b2b2b"  # Dark background
    FG_COLOR = "#ffffff"  # White text
    
    # Header Colors
    HEADER_BG = "#1a1a1a"  # Darker background for header
    
    # Alert Colors
    ALERT_BG = "#ff4444"    # Red for alerts/SCAM
    WARNING_BG = "#ffbb33"  # Yellow/Orange for warnings/SUSPICIOUS
    SAFE_BG = "#00C851"     # Green for safe status
    
    # Sentiment Colors
    SCAM_COLOR = "#ff4444"        # Red
    SUSPICIOUS_COLOR = "#ffbb33"   # Yellow/Orange
    SAFE_COLOR = "#00C851"        # Green
    
    # Button Colors
    BUTTON_BG = "#4285f4"  # Blue
    BUTTON_FG = "#ffffff"  # White
    
    # Dimensions
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    
    # Fonts
    HEADER_FONT = ("Helvetica", 16, "bold")
    TITLE_FONT = ("Helvetica", 14, "bold")
    TEXT_FONT = ("Helvetica", 12)


@dataclass
class MonitoringAlert:
    timestamp: str
    child_name: str
    sentiment: str
    explanation: str
    alert_needed: bool
    message_range: str = ""

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "child_name": self.child_name,
            "sentiment": self.sentiment,
            "explanation": self.explanation,
            "alert_needed": self.alert_needed,
            "message_range": self.message_range,
        }


def load_scammer_info():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            # Prefer phone over email if both exist
            return config.get("scammer_phone") or config.get("scammer_email") or "scammer"
    except Exception as e:
        logging.error(f"Error loading scammer info: {e}")
        return "scammer"


class ParentMonitorWindow:
    def __init__(
        self, alert_queue: queue.Queue, reset_callback: Optional[Callable] = None
    ):
        self.window = tk.Tk()
        self.window.title("Parent Monitoring Dashboard")
        self.window.geometry(
            f"{MonitorStyle.WINDOW_WIDTH}x{MonitorStyle.WINDOW_HEIGHT}"
        )
        self.window.configure(bg=MonitorStyle.BG_COLOR)

        self.alert_queue = alert_queue
        self.alerts = []
        self.monitoring_active = True
        self.reset_callback = reset_callback
        self.is_processing = False
        
        # Load scammer identifier
        self.scammer_id = load_scammer_info()

        # Create logs directory
        self.logs_dir = "monitoring_logs"
        os.makedirs(self.logs_dir, exist_ok=True)

        self.setup_gui()
        self.start_alert_checker()
        # self.load_previous_alerts()

        # Handle window closing
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Bind keyboard shortcuts
        self.window.bind("<Control-r>", lambda e: self.confirm_reset())
        self.window.bind("<Control-m>", lambda e: self.toggle_monitoring())

    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with controls
        header_frame = tk.Frame(main_frame, bg=MonitorStyle.HEADER_BG, height=70)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        # Header label
        header_label = tk.Label(
            header_frame,
            text="Parent Monitoring Dashboard",
            font=MonitorStyle.HEADER_FONT,
            bg=MonitorStyle.HEADER_BG,
            fg="white",
        )
        header_label.pack(side=tk.LEFT, padx=15)

        # Control buttons frame
        control_frame = tk.Frame(header_frame, bg=MonitorStyle.HEADER_BG)
        control_frame.pack(side=tk.RIGHT, padx=15)

        # Monitor toggle button
        self.monitor_button = tk.Button(
            control_frame,
            text="Pause Monitoring",
            command=self.toggle_monitoring,
            bg=MonitorStyle.ALERT_BG,
            fg="white",
        )
        self.monitor_button.pack(side=tk.LEFT, padx=10)

        # Reset button
        self.reset_button = tk.Button(
            control_frame,
            text="Reset Chat",
            command=self.confirm_reset,
            bg=MonitorStyle.WARNING_BG,
            fg="black",
        )
        self.reset_button.pack(side=tk.LEFT, padx=10)

        # Live Monitoring Section
        monitoring_frame = ttk.LabelFrame(
            main_frame, text="Live Chat Monitoring", padding="15"
        )
        monitoring_frame.pack(fill=tk.BOTH, pady=(0, 15))

        # Add processing status indicator
        self.processing_label = ttk.Label(
            monitoring_frame,
            text="",
            font=MonitorStyle.TEXT_FONT,
            foreground="orange"
        )
        self.processing_label.pack(fill=tk.X, pady=(0, 5))
        # self.processing_label.configure(text="Processing messages...")


        # Status indicators
        self.scammer_status = self.create_child_status(monitoring_frame, "scammer")
        self.scammer_status.pack(fill=tk.X, pady=(0, 10))

        # self.victim_status = self.create_child_status(monitoring_frame, "victim")
        # self.victim_status.pack(fill=tk.X)

        # Alerts Section
        alerts_header_frame = ttk.Frame(main_frame)
        alerts_header_frame.pack(fill=tk.X, pady=(15, 10))

        ttk.Label(
            alerts_header_frame,
            text="Chat Analysis Alerts",
            font=MonitorStyle.TITLE_FONT,
        ).pack(side=tk.LEFT)

        ttk.Button(
            alerts_header_frame, text="Export Logs", command=self.export_logs
        ).pack(side=tk.RIGHT)

        # Alerts display
        alerts_frame = ttk.Frame(main_frame)
        alerts_frame.pack(fill=tk.BOTH, expand=True)

        self.alerts_display = tk.Text(
            alerts_frame,
            wrap=tk.WORD,
            font=MonitorStyle.TEXT_FONT,
            height=15,
            padx=15,
            pady=10,
        )
        self.alerts_display.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Scrollbar
        scrollbar = ttk.Scrollbar(alerts_frame, command=self.alerts_display.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.alerts_display.configure(yscrollcommand=scrollbar.set)

        # Configure tags with proper background colors for each sentiment
        self.alerts_display.tag_configure(
            "SCAM",
            background=MonitorStyle.ALERT_BG,
            foreground="white",
            spacing1=5,
            spacing3=5,
        )
        self.alerts_display.tag_configure(
            "SUSPICIOUS",
            background=MonitorStyle.WARNING_BG,
            foreground="black",
            spacing1=5,
            spacing3=5,
        )
        self.alerts_display.tag_configure(
            "SAFE",
            background=MonitorStyle.SAFE_BG,
            foreground="white",
            spacing1=5,
            spacing3=5,
        )

        self.alerts_display.config(state=tk.DISABLED)

    def create_child_status(self, parent, name):
        frame = ttk.Frame(parent)

        # Use scammer_id for the scammer's status
        display_name = self.scammer_id 
        header = ttk.Label(
            frame, text=f"Monitoring Chat With {display_name}", font=MonitorStyle.TITLE_FONT
        )
        header.pack(anchor="w")

        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=5)

        sentiment_label = ttk.Label(
            status_frame, text="Current Sentiment:", font=MonitorStyle.TEXT_FONT
        )
        sentiment_label.pack(side=tk.LEFT, padx=(0, 5))

        sentiment_value = ttk.Label(
            status_frame, text="POSITIVE", font=MonitorStyle.TEXT_FONT
        )
        sentiment_value.pack(side=tk.LEFT)

        # Store reference using original name (scammer/victim) for internal use
        setattr(self, f"{name.lower()}_sentiment", sentiment_value)
        return frame

    def toggle_monitoring(self):
        self.monitoring_active = not self.monitoring_active
        if self.monitoring_active:
            self.monitor_button.configure(
                text="Pause Monitoring", bg=MonitorStyle.ALERT_BG
            )
        else:
            self.monitor_button.configure(
                text="Resume Monitoring", bg=MonitorStyle.SAFE_BG
            )

    def confirm_reset(self):
        if messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset all chat history and analysis?\n"
            "This cannot be undone.",
        ):
            self.reset_monitoring()

    def reset_monitoring(self):
        # Clear alerts
        self.alerts = []

        # Clear displays
        self.alerts_display.config(state=tk.NORMAL)
        self.alerts_display.delete(1.0, tk.END)
        self.alerts_display.config(state=tk.DISABLED)

        # Reset status indicators using scammer_id
        self.update_child_status(self.scammer_id, "SAFE", False)
        self.update_child_status("victim", "SAFE", False)

        # Save empty state
        self.save_empty_state()

        # Call reset callback if provided
        if self.reset_callback:
            self.reset_callback()

        messagebox.showinfo(
            "Reset Complete", "Chat history and analysis have been reset."
        )

    def save_empty_state(self):
        today_file = os.path.join(
            self.logs_dir, f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
        )
        with open(today_file, "w") as f:
            json.dump([], f)

    def update_child_status(self, child_name: str, sentiment: str, alert_needed: bool):
        # Determine which status to update based on whether the name matches scammer_id
        attr_name = (
            "scammer_sentiment"
            if child_name == self.scammer_id
            else "victim_sentiment"
        )
        sentiment_label = getattr(self, attr_name)
        sentiment_label.configure(text=sentiment)

        color = (
            MonitorStyle.ALERT_BG
            if alert_needed
            else (
                MonitorStyle.WARNING_BG
                if sentiment == "SUSPICIOUS"
                else MonitorStyle.SAFE_BG
            )
        )
        sentiment_label.configure(foreground=color)

    def update_processing_status(self, is_processing: bool):
        """Update the processing status indicator"""
        self.is_processing = is_processing
        if is_processing:
            self.processing_label.configure(text="Processing messages...")
        else:
            self.processing_label.configure(text="")

    def add_alert(self, alert: MonitoringAlert):
        self.update_processing_status(False)  # Clear processing status when alert arrives
        self.alerts.append(alert)
        self.save_alert(alert)

        if not self.monitoring_active:
            return

        self.alerts_display.config(state=tk.NORMAL)

        alert_text = (
            f"[{alert.timestamp}] {alert.child_name}\n"
            f"Analysis Range: {alert.message_range}\n"
            f"Sentiment: {alert.sentiment}\n"
            f"Alert Needed: {'Yes' if alert.alert_needed else 'No'}\n"
            f"Analysis: {alert.explanation}\n"
            f"{'-' * 50}\n\n"
        )

        # Use exact sentiment as tag name
        self.alerts_display.insert("1.0", alert_text, alert.sentiment)
        self.alerts_display.see("1.0")
        self.alerts_display.config(state=tk.DISABLED)

        self.update_child_status(alert.child_name, alert.sentiment, alert.alert_needed)

    def save_alert(self, alert: MonitoringAlert):
        filename = os.path.join(
            self.logs_dir, f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
        )

        existing_alerts = []
        if os.path.exists(filename):
            with open(filename, "r") as f:
                existing_alerts = json.load(f)

        existing_alerts.append(alert.to_dict())

        with open(filename, "w") as f:
            json.dump(existing_alerts, f, indent=2)

    def load_previous_alerts(self):
        try:
            today_file = os.path.join(
                self.logs_dir, f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
            )
            if os.path.exists(today_file):
                try:
                    with open(today_file, "r") as f:
                        alerts = json.load(f)
                        for alert_data in alerts:
                            alert = MonitoringAlert(**alert_data)
                            self.add_alert(alert)
                except json.JSONDecodeError as e:
                    logging.warning(f"Previous alerts file is corrupted: {e}")
                    # Backup the corrupted file
                    backup_file = today_file + ".corrupted"
                    os.rename(today_file, backup_file)
                    # Create new empty alerts file
                    with open(today_file, "w") as f:
                        json.dump([], f)
                    logging.info(
                        f"Created new empty alerts file. Corrupted file backed up to {backup_file}"
                    )
        except Exception as e:
            logging.error(f"Error loading previous alerts: {e}")
            # Continue without loading previous alerts
            pass

    def export_logs(self):
        filename = f"monitoring_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(filename, "w") as f:
            f.write("Chat Monitoring Logs\n")
            f.write("=" * 50 + "\n\n")

            for alert in self.alerts:
                f.write(f"Time: {alert.timestamp}\n")
                f.write(f"Child: {alert.child_name}\n")
                f.write(f"Message Range: {alert.message_range}\n")
                f.write(f"Sentiment: {alert.sentiment}\n")
                f.write(f"Alert Needed: {'Yes' if alert.alert_needed else 'No'}\n")
                f.write(f"Analysis: {alert.explanation}\n")
                f.write("-" * 50 + "\n\n")

        messagebox.showinfo("Export Complete", f"Logs exported to {filename}")

    def start_alert_checker(self):
        def check_alerts():
            if self.monitoring_active:
                try:
                    alert = self.alert_queue.get_nowait()
                    if alert:
                        self.add_alert(alert)
                except queue.Empty:
                    # if not self.is_processing:  # Commented out processing status check
                    #     self.update_processing_status(True)
                    pass
            self.window.after(100, check_alerts)

        self.window.after(100, check_alerts)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to stop monitoring?"):
            self.monitoring_active = False
            self.window.destroy()

    def run(self):
        self.window.mainloop()

    
if __name__ == "__main__":
    # Test code
    test_queue = queue.Queue()
    window = ParentMonitorWindow(test_queue)
    window.run()