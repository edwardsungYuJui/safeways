# messenger_chat.py
import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from queue import Queue
import queue
from client import ChatMonitorClient, Chat, SentimentResponse
from datetime import datetime
import uuid
import nest_asyncio
from parent_monitor import ParentMonitorWindow, MonitoringAlert, MonitorStyle
import signal
import sys
from typing import List, Optional
import logging
import webbrowser
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="chat_app.log",
)

# Apply nest_asyncio for nested event loops
nest_asyncio.apply()


class MessengerStyle:
    # Colors
    BG_COLOR = "#f0f2f5"  # Light gray background
    SENT_BG = "#0084ff"  # Facebook Messenger blue
    RECEIVED_BG = "#e4e6eb"
    SENT_FG = "#ffffff"
    RECEIVED_FG = "#050505"
    INPUT_BG = "#ffffff"  # White background for input
    INPUT_FG = "#000000"  # Black text for input

    # Fonts
    HEADER_FONT = ("Helvetica", 14, "bold")
    MESSAGE_FONT = ("Helvetica", 12)
    INPUT_FONT = ("Helvetica", 12, "bold")  # Bold font for input

    # Dimensions
    WINDOW_WIDTH = 400  # Increased width
    WINDOW_HEIGHT = 600  # Increased height

    # Padding and margins
    MESSAGE_PADDING = 12
    BUBBLE_RADIUS = 20  # For rounded corners


class AsyncTkThread:
    """Handles async operations in a separate thread"""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.running = True
        self.thread.start()
        logging.info("AsyncTkThread initialized")

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        while self.running:
            try:
                self.loop.run_forever()
            except Exception as e:
                logging.error(f"AsyncTkThread error: {e}")
                if self.running:
                    continue
                break

    def run(self, coro):
        if not self.running:
            return None
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=30)
        except Exception as e:
            logging.error(f"Async operation error: {e}")
            return None

    def stop(self):
        self.running = False
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        logging.info("AsyncTkThread stopped")


class RoundedCanvas(tk.Canvas):
    def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class ChatWindow:
    """Individual chat window for each user"""

    def __init__(
        self,
        name: str,
        other_name: str,
        client: ChatMonitorClient,
        message_callback,
        on_close: Optional[callable] = None,
    ):
        self.window = tk.Tk()
        self.window.title(f"{name}'s Chat")
        self.window.geometry(
            f"{MessengerStyle.WINDOW_WIDTH}x{MessengerStyle.WINDOW_HEIGHT}"
        )
        self.window.configure(bg=MessengerStyle.BG_COLOR)

        self.name = name
        self.other_name = other_name
        self.client = client
        self.message_callback = message_callback
        self.on_close = on_close
        self.help_button = None  # Initialize help button reference

        self.update_interval = 1000  # Update every 1000 milliseconds (1 second)
        self.schedule_updates()

        self.setup_gui()
        self.window.protocol("WM_DELETE_WINDOW", self.handle_close)
        logging.info(f"ChatWindow initialized for {name}")

    def schedule_updates(self):
        """Schedule regular updates to the chat display."""
        self.update_chat_display()
        self.window.after(self.update_interval, self.schedule_updates)

    def update_chat_display(self):
        """Update the chat display with new messages or changes."""
        # Logic to refresh or update the chat display
        # For example, check for new messages and display them
        logging.info("Chat display updated")
        # ... additional update logic ...

    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with counter
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        header = ttk.Label(
            header_frame,
            text=f"Chat with {self.other_name}",
            font=MessengerStyle.HEADER_FONT,
        )
        header.pack(side=tk.LEFT)

        self.message_counter = ttk.Label(
            header_frame, text="Messages: 0", font=MessengerStyle.MESSAGE_FONT
        )
        self.message_counter.pack(side=tk.RIGHT)

        # Chat area
        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_display = tk.Text(
            chat_frame,
            wrap=tk.WORD,
            font=MessengerStyle.MESSAGE_FONT,
            bg=MessengerStyle.BG_COLOR,
            padx=15,
            pady=10,
            relief=tk.FLAT,
            cursor="arrow",  # Hide text cursor
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Scrollbar
        scrollbar = ttk.Scrollbar(chat_frame)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.chat_display.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.chat_display.yview)

        # Create input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(10, 0))

        # Create a frame to hold the text entry and give it a border
        border_frame = tk.Frame(
            input_frame,
            bg=MessengerStyle.BG_COLOR,
            highlightbackground="#ddd",
            highlightthickness=1,
            bd=0,
        )
        border_frame.pack(side=tk.LEFT, padx=(0, 10), expand=False)

        # Create the message entry with fixed width
        self.message_entry = tk.Text(
            border_frame,
            height=2,
            width=30,  # Added fixed width in characters
            font=MessengerStyle.INPUT_FONT,
            wrap=tk.WORD,
            bg=MessengerStyle.INPUT_BG,
            fg=MessengerStyle.INPUT_FG,
            relief=tk.FLAT,
            padx=10,
            pady=5,
        )
        self.message_entry.pack(fill=tk.BOTH, expand=True)

        # Create buttons frame
        self.buttons_frame = ttk.Frame(input_frame)
        self.buttons_frame.pack(side=tk.RIGHT)

        # Create help button (initially hidden)
        self.help_button = tk.Button(
            self.buttons_frame,
            text="Help",
            command=self.open_help_website,
            bg='red',
            fg='white',
            highlightbackground='red'  # For macOS
        )
        # Don't pack the help button yet - will be shown when needed

        # Create send button
        self.send_button = ttk.Button(
            self.buttons_frame,
            text="Send",
            command=self.send_message,
            style="Custom.TButton"
        )
        self.send_button.pack(side=tk.RIGHT)

        # Configure message bubble tags with rounded corners and better spacing
        self.chat_display.tag_configure(
            "sent",
            justify="right",
            background=MessengerStyle.SENT_BG,
            foreground=MessengerStyle.SENT_FG,
            spacing1=8,
            spacing3=8,
            rmargin=15,
            lmargin1=50,  # Indentation for sent messages
        )
        self.chat_display.tag_configure(
            "received",
            justify="left",
            background=MessengerStyle.RECEIVED_BG,
            foreground=MessengerStyle.RECEIVED_FG,
            spacing1=8,
            spacing3=8,
            lmargin1=15,
            rmargin=50,  # Indentation for received messages
        )

        # Bind keys
        self.message_entry.bind(
            "<Return>", lambda e: "break" if self.send_message() else None
        )
        self.message_entry.bind("<Shift-Return>", lambda e: None)

        # Initial state
        self.chat_display.config(state=tk.DISABLED)
        self.message_count = 0
        self.update_counter()

    def update_counter(self):
        self.message_counter.config(text=f"Messages: {self.message_count}")

    def send_message(self) -> bool:
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message:
            return False

        self.message_entry.delete("1.0", tk.END)
        self.message_count += 1
        self.update_counter()
        self.display_message(self.name, message, is_self=True)
        self.message_callback(self.name, message)
        return True

    def display_message(self, sender: str, message: str, is_self: bool = False):
        self.chat_display.config(state=tk.NORMAL)

        # Add spacing before message
        self.chat_display.insert(tk.END, "\n")

        # Get current timestamp
        timestamp = datetime.now().strftime("%H:%M")

        # Create and insert message bubble with sender and timestamp
        bubble = self.create_message_bubble(sender, message, timestamp, is_self)
        bubble_window = self.chat_display.window_create(
            tk.END, window=bubble, padx=20, pady=5
        )

        # Add a newline after the message
        self.chat_display.insert(tk.END, "\n")

        # Align message to right or left
        if is_self:
            bubble.pack(anchor="e")
        else:
            bubble.pack(anchor="w")

        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def clear_chat(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.message_entry.delete(1.0, tk.END)
        self.message_count = 0
        self.update_counter()
        logging.info(f"Chat cleared for {self.name}")

    def handle_close(self):
        if self.on_close:
            self.on_close()
        self.window.destroy()
        logging.info(f"ChatWindow closed for {self.name}")

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Create a rounded rectangle"""
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.chat_display.create_polygon(points, smooth=True, **kwargs)

    def create_message_bubble(self, sender: str, message: str, timestamp: str, is_self=False):
        """Create a message bubble with sender name and timestamp"""
        # Main container for the entire message (sender, timestamp, and bubble)
        container = tk.Frame(
            self.chat_display,
            bg=MessengerStyle.BG_COLOR,
            padx=MessengerStyle.MESSAGE_PADDING,
            pady=MessengerStyle.MESSAGE_PADDING // 2,
        )

        # Frame for sender name and timestamp
        header_frame = tk.Frame(container, bg=MessengerStyle.BG_COLOR)
        header_frame.pack(fill=tk.X, pady=(0, 2))

        # Sender name label
        sender_label = tk.Label(
            header_frame,
            text=sender,
            font=("Helvetica", 10, "bold"),
            fg="#65676B",
            bg=MessengerStyle.BG_COLOR,
        )
        
        # Timestamp label
        time_label = tk.Label(
            header_frame,
            text=timestamp,
            font=("Helvetica", 9),
            fg="#65676B",
            bg=MessengerStyle.BG_COLOR,
        )

        # Position sender and timestamp based on message alignment
        if is_self:
            sender_label.pack(side=tk.RIGHT, padx=(0, 5))
            time_label.pack(side=tk.RIGHT)
        else:
            sender_label.pack(side=tk.LEFT, padx=(5, 0))
            time_label.pack(side=tk.LEFT)

        # Message bubble frame
        bubble_frame = tk.Frame(
            container,
            bg=MessengerStyle.BG_COLOR,
            padx=MessengerStyle.MESSAGE_PADDING,
            pady=MessengerStyle.MESSAGE_PADDING // 2,
        )
        bubble_frame.pack(fill=tk.X)

        # Create the rounded rectangle for the message
        shape = RoundedCanvas(
            bubble_frame,
            width=250,
            height=50,
            bg=MessengerStyle.BG_COLOR,
            highlightthickness=0,
        )
        shape.create_rounded_rectangle(
            2,
            2,
            248,
            48,
            radius=MessengerStyle.BUBBLE_RADIUS,
            fill=MessengerStyle.SENT_BG if is_self else MessengerStyle.RECEIVED_BG,
        )
        shape.pack(expand=True, fill=tk.BOTH)

        # Message text label
        label = tk.Label(
            bubble_frame,
            text=message,
            wraplength=230,
            justify=tk.LEFT,
            bg=MessengerStyle.SENT_BG if is_self else MessengerStyle.RECEIVED_BG,
            fg=MessengerStyle.SENT_FG if is_self else MessengerStyle.RECEIVED_FG,
            font=MessengerStyle.MESSAGE_FONT,
        )
        label.place(x=10, y=10)

        return container

    def update_message_bubble(self, frame, is_self):
        """Update the message bubble shape"""
        frame.update_idletasks()
        width = frame.winfo_width()
        height = frame.winfo_height()

        if not hasattr(frame, "shape"):
            frame.shape = RoundedCanvas(
                frame,
                width=width,
                height=height,
                bg=MessengerStyle.BG_COLOR,
                highlightthickness=0,
            )
            frame.shape.place(x=0, y=0)

        frame.shape.delete("all")
        frame.shape.create_rounded_rectangle(
            2,
            2,
            width - 2,
            height - 2,
            radius=MessengerStyle.BUBBLE_RADIUS,
            fill=MessengerStyle.SENT_BG if is_self else MessengerStyle.RECEIVED_BG,
        )

    def update_input_container(self, container):
        """Update the input container shape"""
        container.update_idletasks()
        width = container.winfo_width()
        height = container.winfo_height()

        if not hasattr(container, "shape"):
            container.shape = RoundedCanvas(
                container,
                width=width,
                height=height,
                bg=MessengerStyle.BG_COLOR,
                highlightthickness=0,
            )
            container.shape.lower()  # Place the shape behind other widgets

        container.shape.configure(width=width, height=height)
        container.shape.delete("all")
        container.shape.create_rounded_rectangle(
            2,
            2,
            width - 2,
            height - 2,
            radius=MessengerStyle.BUBBLE_RADIUS,
            fill=MessengerStyle.INPUT_BG,
        )

    def open_help_website(self):
        """Open the help website in the default browser"""
        # Create a new window for user input
        input_window = tk.Toplevel(self.window)
        input_window.title("Help Input")

        # Labels and Entry fields for user input
        tk.Label(input_window, text="Please describe what happened:").pack()
        what_entry = tk.Entry(input_window, width=50)
        what_entry.pack(pady=5)

        tk.Label(input_window, text="Please specify when it happened:").pack()
        when_entry = tk.Entry(input_window, width=50)
        when_entry.pack(pady=5)

        tk.Label(input_window, text="Please indicate where it happened:").pack()
        where_entry = tk.Entry(input_window, width=50)
        where_entry.pack(pady=5)

        # Label to display guidelines
        guidelines_label = tk.Label(input_window, text="", wraplength=400)
        guidelines_label.pack(pady=10)

        def submit():
            what = what_entry.get()
            when = when_entry.get()
            where = where_entry.get()

            # Disable the submit button to prevent multiple submissions
            submit_button.config(state=tk.DISABLED)

            # Call the LLM asynchronously
            guidelines_label.config(text="Fetching guidelines...")  # Indicate loading
            self.async_handler.run(self.fetch_guidelines(what, when, where, guidelines_label))

            # Clear the entry fields after submission
            what_entry.delete(0, tk.END)
            when_entry.delete(0, tk.END)
            where_entry.delete(0, tk.END)

        # Submit button
        submit_button = tk.Button(input_window, text="Submit", command=submit)
        submit_button.pack(pady=10)

        # Focus on the first entry field
        what_entry.focus_set()

    def fetch_guidelines(self, what: str, when: str, where: str, guidelines_label):
        """Fetch guidelines from the LLM and update the label"""
        guidelines = self.get_guidelines_from_llm(what, when, where)
        guidelines_label.config(text=guidelines)  # Display guidelines in the label

    def get_guidelines_from_llm(self, what: str, when: str, where: str) -> str:
        """Interact with an LLM using Ollama to get guidelines based on user input"""
        from ollama import chat
        from ollama import ChatResponse
        from pydantic import BaseModel

        class GuidelinesResponse(BaseModel):
            guidelines: str

        # Construct the prompt for the LLM
        prompt = f"""[INST] <<SYS>>
        You are a helpful assistant. Please provide guidelines to mitigate the scam issue based on the user's input.
        User input:
        What: {what}
        When: {when}
        Where: {where}
        <</SYS>>
        Please respond with the guidelines.
        <</INST>>"""

        # Call the Ollama chat function
        response: ChatResponse = chat(
            model="deepseek-r1:8b",  # Replace with your actual model name
            messages=[{"role": "user", "content": prompt, "temperature": 0.0}],
            format=GuidelinesResponse.model_json_schema(),
            stream=False,
        )
        
        # Validate and extract the response
        output = GuidelinesResponse.model_validate_json(response.message.content)
        return output.guidelines

    def show_help_button(self, show: bool = True):
        """Show or hide the help button based on sentiment analysis"""
        try:
            logging.info(f"Attempting to {'show' if show else 'hide'} help button for {self.name}")
            if show and self.help_button is not None:
                # Remove the button first in case it's already packed
                self.help_button.pack_forget()
                
                # Pack the help button to the left of the send button
                self.help_button.pack(side=tk.RIGHT, padx=(0, 5), before=self.send_button)
                
                # Force button to be visible and on top
                self.help_button.lift()
                self.help_button.update()
                
                # Force the buttons frame to update
                self.buttons_frame.update_idletasks()
                self.buttons_frame.update()
                
                # Force main window update
                self.window.update_idletasks()
                self.window.update()
                
                logging.info(f"Help button shown for {self.name}")
            elif not show and self.help_button is not None:
                self.help_button.pack_forget()
                self.buttons_frame.update_idletasks()
                self.window.update_idletasks()
                logging.info(f"Help button hidden for {self.name}")
        except Exception as e:
            logging.error(f"Error managing help button visibility: {e}")
            import traceback
            traceback.print_exc()

    def update_sentiment_status(self, sentiment: str):
        """Update UI based on sentiment analysis results"""
        try:
            logging.info(f"Updating sentiment status for {self.name}: {sentiment}")
            
            # Schedule the UI updates to run in the main thread
            def update_ui():
                self.show_help_button(True)
                
                # Force window refresh
                self.window.update_idletasks()
                self.window.update()
            
            # Ensure UI updates happen in the main thread
            if self.window.winfo_exists():
                self.window.after(0, update_ui)
                
        except Exception as e:
            logging.error(f"Error updating sentiment status: {e}")
            import traceback
            traceback.print_exc()


def load_scammer_info():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            # Prefer phone over email if both exist
            return config.get("scammer_phone") or config.get("scammer_email") or "scammer"
    except Exception as e:
        logging.error(f"Error loading scammer info: {e}")
        return "scammer"


class MessengerChat:
    """Main chat application controller"""

    def __init__(self):
        print("Initializing MessengerChat...")
        self.async_handler = AsyncTkThread()
        self.client = ChatMonitorClient()
        self.message_queue = Queue()
        self.alert_queue = queue.Queue()
        self.current_chat = []
        self.running = True

        # Load scammer identifier from config
        self.scammer_id = load_scammer_info()

        print("Creating windows...")
        # Create windows with scammer identifier
        self.parent_window = ParentMonitorWindow(
            self.alert_queue, reset_callback=self.reset_chat
        )
        self.scammer_window = ChatWindow(
            self.scammer_id, "victim", self.client, self.handle_message, self.stop_application
        )
        self.victim_window = ChatWindow(
            "victim", self.scammer_id, self.client, self.handle_message, self.stop_application
        )

        print("Positioning windows...")
        self.position_windows()
        print("Starting analysis checker...")
        self.start_analysis_checker()

        # Sliding window configuration
        self.window_size = 1  # Size of analysis window
        self.last_analyzed_index = -1  # Track last analyzed message
        self.messages_since_analysis = 0  # Counter for messages since last analysis

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logging.info(
            f"MessengerChat initialized with sliding window size: {self.window_size}"
        )

    def get_analysis_window(self) -> List[Chat]:
        """Get the current sliding window of messages"""
        if len(self.current_chat) <= self.window_size:
            return self.current_chat
        return self.current_chat[-self.window_size :]

    def should_analyze(self) -> bool:
        """Determine if analysis should be performed"""
        total_messages = len(self.current_chat)

        # First analysis when we reach window_size
        if total_messages == self.window_size and self.last_analyzed_index == -1:
            return True

        # After first window, only analyze when we have window_size new messages
        if self.messages_since_analysis >= self.window_size:
            return True

        return False

    def position_windows(self):
        screen_width = self.scammer_window.window.winfo_screenwidth()
        screen_height = self.scammer_window.window.winfo_screenheight()

        chat_width = MessengerStyle.WINDOW_WIDTH
        chat_height = MessengerStyle.WINDOW_HEIGHT
        monitor_width = MonitorStyle.WINDOW_WIDTH
        monitor_height = MonitorStyle.WINDOW_HEIGHT

        scammer_x = (screen_width // 4) - (chat_width // 2)
        scammer_y = (screen_height // 2) - (chat_height // 2)
        self.scammer_window.window.geometry(
            f"{chat_width}x{chat_height}+{scammer_x}+{scammer_y}"
        )

        victim_x = (3 * screen_width // 4) - (chat_width // 2)
        victim_y = scammer_y
        self.victim_window.window.geometry(
            f"{chat_width}x{chat_height}+{victim_x}+{victim_y}"
        )

        parent_x = (screen_width - monitor_width) // 2
        self.parent_window.window.geometry(
            f"{monitor_width}x{monitor_height}+{parent_x}+0"
        )

        # Raise windows
        for window in [
            self.parent_window.window,
            self.scammer_window.window,
            self.victim_window.window,
        ]:
            window.lift()
            window.focus_force()

    def handle_message(self, sender: str, message: str):
        """Handle new message from a chat window"""
        self.current_chat.append(Chat(sender=sender, message=message))
        self.messages_since_analysis += 1

        # Display in other window using scammer_id
        if sender == self.scammer_id:
            self.victim_window.display_message(self.scammer_id, message, is_self=False)
            self.victim_window.message_count += 1
            self.victim_window.update_counter()
        else:
            self.scammer_window.display_message("victim", message, is_self=False)
            self.scammer_window.message_count += 1
            self.scammer_window.update_counter()

        # Log message stats
        logging.debug(
            f"Messages: total={len(self.current_chat)}, since_analysis={self.messages_since_analysis}"
        )

        # Analyze if needed
        if self.should_analyze():

            def analyze_wrapper():
                try:
                    analysis_window = self.get_analysis_window()
                    logging.info(f"Analyzing window of {len(analysis_window)} messages")

                    results = self.async_handler.run(
                        self.client.analyze_chats(
                            username=f"{sender}_demo", chats=analysis_window
                        )
                    )

                    if results:
                        self.message_queue.put((sender, results))
                        self.last_analyzed_index = len(self.current_chat) - 1
                        self.messages_since_analysis = 0
                        logging.info(
                            f"Analysis complete. Next analysis after {self.window_size} more messages"
                        )

                except Exception as e:
                    logging.error(f"Analysis error: {e}")

            threading.Thread(target=analyze_wrapper, daemon=True).start()

    def reset_chat(self):
        """Reset chat and analysis state"""
        try:
            self.current_chat = []
            self.last_analyzed_index = -1
            self.messages_since_analysis = 0

            # Clear chat windows
            self.scammer_window.clear_chat()
            self.victim_window.clear_chat()

            # Clear queues
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                except queue.Empty:
                    break

            while not self.alert_queue.empty():
                try:
                    self.alert_queue.get_nowait()
                except queue.Empty:
                    break

            logging.info("Chat system reset")
        except Exception as e:
            logging.error(f"Error resetting chat: {e}")
            # Optionally, you can show a message box to inform the user
            messagebox.showerror("Error", "Failed to reset chat. Please try again.")

    def start_analysis_checker(self):
        """Start the analysis checking loop"""

        def check_analysis():
            try:
                sender, results = self.message_queue.get_nowait()
                if results:
                    # Calculate the exact message range that was analyzed
                    if len(self.current_chat) <= self.window_size:
                        start_msg = 1
                    else:
                        start_msg = len(self.current_chat) - self.window_size + 1
                    end_msg = len(self.current_chat)

                    alert = MonitoringAlert(
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        child_name=sender,
                        sentiment=results.sentiment,
                        explanation=results.explanation,
                        alert_needed=results.alert_needed,
                        message_range=f"Messages {start_msg} - {end_msg} (Window of {self.window_size})",
                    )
                    self.alert_queue.put(alert)
                    
                    # Update the chat windows with sentiment status
                    if sender == self.scammer_id:
                        self.victim_window.update_sentiment_status(results.sentiment)
                    else:
                        self.scammer_window.update_sentiment_status(results.sentiment)
                    
                    logging.info(
                        f"Analysis results for messages {start_msg}-{end_msg}: {results.sentiment}"
                    )

            except queue.Empty:
                pass
            finally:
                if self.running:
                    self.scammer_window.window.after(100, check_analysis)

        self.scammer_window.window.after(100, check_analysis)

    def signal_handler(self, signum, frame):
        """Handle system signals"""
        print("\nReceived signal to terminate. Cleaning up...")
        logging.info(f"Received signal {signum}")
        self.stop_application()

    def stop_application(self):
        """Clean shutdown of the application"""
        if not self.running:
            return

        self.running = False
        logging.info("Stopping application")

        if self.async_handler:
            self.async_handler.stop()

        for window in [
            self.parent_window.window,
            self.victim_window.window,
            self.scammer_window.window,
        ]:
            try:
                window.destroy()
            except:
                pass

        logging.info("Application stopped")
        sys.exit(0)

    def run(self):
        """Start the application"""
        try:
            logging.info("Starting application")
            self.parent_window.window.mainloop()
        except Exception as e:
            logging.error(f"Application error: {e}")
        finally:
            self.stop_application()


if __name__ == "__main__":
    try:
        # Configure logging with both file and console output
        logging.basicConfig(
            level=logging.DEBUG,  # Changed from INFO to DEBUG
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("chat_app.log"),
                logging.StreamHandler(sys.stdout),  # Add console output
            ],
        )

        print("Starting Chat Application...")  # Add print statement
        logging.debug("Initializing Chat Application")

        # Start the application
        chat_app = MessengerChat()
        print("Created MessengerChat instance")  # Add print statement
        logging.debug("MessengerChat instance created")

        print("Running chat application...")  # Add print statement
        chat_app.run()

    except Exception as e:
        print(f"Error starting application: {e}")  # Add print statement
        logging.exception("Application failed to start")  # Log full traceback
        sys.exit(1)
