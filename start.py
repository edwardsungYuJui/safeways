import subprocess
import sys
import time
import os
from pathlib import Path
import importlib.util
import json

def import_demo_setup():
    # Dynamically import DemoSetupWindow from demo_setup.py
    demo_setup_path = Path(__file__).parent / "demo_setup.py"
    spec = importlib.util.spec_from_file_location("demo_setup", demo_setup_path)
    demo_setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo_setup)
    return demo_setup.DemoSetupWindow

def start_services():
    # Get the current directory
    root_dir = Path(__file__).parent
    
    # First, run the demo setup
    print("Starting demo setup...")
    DemoSetupWindow = import_demo_setup()
    demo_setup = DemoSetupWindow()
    demo_setup.window.mainloop()
    
    # Check if demo was cancelled
    if not demo_setup.demo_data:
        print("Demo setup was cancelled")
        return
        
    # Store demo data in environment variables so the client can access it
    os.environ["DEMO_PHONE"] = demo_setup.demo_data["scammer_phone"]
    os.environ["DEMO_EMAIL"] = demo_setup.demo_data["scammer_email"]
    os.environ["DEMO_TIMESTAMP"] = demo_setup.demo_data["scammer_timestamp"]
    
    # After getting demo_data, write to config file
    with open("config.json", "w") as f:
        json.dump(demo_setup.demo_data, f)
    
    server_dir = root_dir / "server"
    
    # Start the server from the server directory
    print("Starting server...")
    server_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=str(server_dir),
                                    text=True,
                                    bufsize=1)
    
    # Function to print output from a process
    def print_output(process, prefix):
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(f"{prefix}: {line.strip()}")
    
    # Start reading server output in the background
    import threading
    server_thread = threading.Thread(target=print_output, args=(server_process, "Server"), daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("Waiting for server to initialize...")
    time.sleep(3)
    
    if server_process.poll() is not None:
        # Server failed to start
        error = server_process.stderr.read()
        print(f"Server failed to start. Error:\n{error}")
        return
    
    # Start the client
    print("Starting client...")
    client_process = subprocess.Popen([sys.executable, str(root_dir / "client" / "messenger_chat.py")],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    bufsize=1)
    
    # Start reading client output in the background
    client_thread = threading.Thread(target=print_output, args=(client_process, "Client"), daemon=True)
    client_thread.start()
    
    try:
        # Keep the script running until Ctrl+C is pressed
        while True:
            # Check if either process has died
            if server_process.poll() is not None:
                print("Server process died!")
                break
            if client_process.poll() is not None:
                print("Client process died!")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down services...")
    finally:
        server_process.terminate()
        client_process.terminate()
        server_process.wait()
        client_process.wait()
        print("Services stopped")

if __name__ == "__main__":
    start_services() 