import tkinter as tk
from tkinter import ttk

class DemoSetupWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Demo Setup")
        self.window.geometry("500x500")
        
        # Variables to hold input values
        self.country_code_var = tk.StringVar()
        self.area_code_var = tk.StringVar()
        self.prefix_var = tk.StringVar()
        self.line_number_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.timestamp_var = tk.StringVar()
        
        # Set default timestamp
        self.timestamp_var.set("00:00")
        
        # This will store the demo configuration after the window closes
        self.demo_data = None
        
        self.setup_ui()
    
    def setup_ui(self):
        frame = ttk.Frame(self.window, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # Phone Number Input
        phone_label = ttk.Label(frame, text="Scammer Phone Number:")
        phone_label.pack(anchor="w", pady=(0, 5))
        
        # Create a frame for phone number components
        phone_frame = ttk.Frame(frame)
        phone_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Country code input (with + prefix)
        plus_label = ttk.Label(phone_frame, text="+")
        plus_label.pack(side=tk.LEFT)
        country_code_entry = ttk.Entry(phone_frame, textvariable=self.country_code_var, width=3)
        country_code_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Area code input
        area_code_entry = ttk.Entry(phone_frame, textvariable=self.area_code_var, width=4)
        area_code_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Prefix input
        prefix_entry = ttk.Entry(phone_frame, textvariable=self.prefix_var, width=4)
        prefix_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Line number input
        line_number_entry = ttk.Entry(phone_frame, textvariable=self.line_number_var, width=5)
        line_number_entry.pack(side=tk.LEFT)
        
        # Add input validation and auto-focus
        country_code_entry.config(validate="key", validatecommand=(frame.register(lambda P: len(P) <= 2 and (P == "" or P.isdigit())), '%P'))
        area_code_entry.config(validate="key", validatecommand=(frame.register(lambda P: len(P) <= 3 and (P == "" or P.isdigit())), '%P'))
        prefix_entry.config(validate="key", validatecommand=(frame.register(lambda P: len(P) <= 3 and (P == "" or P.isdigit())), '%P'))
        line_number_entry.config(validate="key", validatecommand=(frame.register(lambda P: len(P) <= 4 and (P == "" or P.isdigit())), '%P'))
        
        # Auto-advance to next field
        def on_entry_filled(event, current_entry, next_entry=None):
            if next_entry and len(current_entry.get()) >= int(current_entry.config('width')[4]) - 1:
                next_entry.focus()
        
        country_code_entry.bind('<KeyRelease>', lambda e: on_entry_filled(e, country_code_entry, area_code_entry))
        area_code_entry.bind('<KeyRelease>', lambda e: on_entry_filled(e, area_code_entry, prefix_entry))
        prefix_entry.bind('<KeyRelease>', lambda e: on_entry_filled(e, prefix_entry, line_number_entry))
        
        # Email Input
        email_label = ttk.Label(frame, text="Scammer Email:")
        email_label.pack(anchor="w", pady=(0, 5))
        email_entry = ttk.Entry(frame, textvariable=self.email_var)
        email_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Timestamp Input
        timestamp_label = ttk.Label(frame, text="Scam Timestamp (EST):")
        timestamp_label.pack(anchor="w", pady=(0, 5))
        
        # Create list of hours in 24-hour format
        hours = [f"{hour:02d}:00" for hour in range(24)]
        timestamp_combobox = ttk.Combobox(frame, textvariable=self.timestamp_var, values=hours, state="readonly")
        timestamp_combobox.pack(fill=tk.X, pady=(0, 15))
        
        # Start Demo Button
        start_button = ttk.Button(frame, text="Start Demo", command=self.start_demo)
        start_button.pack(pady=(10, 0))
    
    def start_demo(self):
        # Combine phone number components
        full_phone = f"{self.country_code_var.get()}{self.area_code_var.get()}{self.prefix_var.get()}{self.line_number_var.get()}"
        
        # Retrieve and store the demo preset values
        self.demo_data = {
            "scammer_phone": full_phone,
            "scammer_email": self.email_var.get(),
            "scammer_timestamp": self.timestamp_var.get()
        }
        print("Demo preset values:", self.demo_data)
        
        # Destroy the demo setup window.
        self.window.destroy()
        
        # Here you can launch the chat application and pass the demo_data if needed.
        # For example:
        

if __name__ == "__main__":
    demo_setup = DemoSetupWindow()
    demo_setup.window.mainloop() 