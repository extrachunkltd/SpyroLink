import tkinter as tk
from tkinter import scrolledtext
import usb.core
import usb.util
import threading
import time

class PortalInspector:
    def __init__(self, root):
        self.root = root
        self.root.title("Spyro Link")
        self.root.geometry("600x500")
        
        self.log_area = scrolledtext.ScrolledText(root, height=20, width=70, bg="#1a1a1a", fg="#00ff00")
        self.log_area.pack(pady=10)

        self.btn = tk.Button(root, text="Get Device Details", command=self.start)
        self.btn.pack()

    def log(self, msg):
        self.log_area.insert(tk.END, f"> {msg}\n")
        self.log_area.see(tk.END)

    def start(self):
        threading.Thread(target=self.run_logic, daemon=True).start()

    def run_logic(self):
        try:
            # 1. Find device
            dev = usb.core.find(idVendor=0x1430, idProduct=0x0150)
            if dev is None:
                self.log("Device not found! Is it plugged in?")
                return

            # 2. Setup Configuration
            dev.set_configuration()
            cfg = dev.get_active_configuration()
            intf = cfg[(0,0)]

            # 3. FIX: Find endpoints and explicitly store their bEndpointAddress
            ep_out_obj = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
            ep_in_obj = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

            if ep_out_obj is None or ep_in_obj is None:
                self.log("Failed to find valid endpoints. Check Zadig driver.")
                return

            # Store the actual integer addresses
            addr_out = ep_out_obj.bEndpointAddress
            addr_in = ep_in_obj.bEndpointAddress

            self.log(f"--- Hardware Found ---")
            self.log(f"Manufacturer: {usb.util.get_string(dev, dev.iManufacturer)}")
            self.log(f"Product:      {usb.util.get_string(dev, dev.iProduct)}")
            self.log(f"Address IN:   {hex(addr_in)}")
            self.log(f"Address OUT:  {hex(addr_out)}")

            # 4. Request Version ('v' command)
            # We use the raw addr_out instead of the object to prevent attribute errors
            dev.write(addr_out, b'v' + b'\x00' * 31)
            ver_res = dev.read(addr_in, 32, timeout=1000)
            
            self.log(f"Firmware:     v{ver_res[1]}.{ver_res[2]}")
            
            # 5. Reset and Watch for Data
            dev.write(addr_out, b'R' + b'\x00' * 31)
            self.log("Portal Initialized. Place a figure on top.")

            while True:
                dev.write(addr_out, b'S' + b'\x00' * 31)
                try:
                    data = dev.read(addr_in, 32, timeout=500)
                    if data and data[1] != 0:
                        self.log(f"Character UID: {data.hex()[2:18].upper()}")
                except usb.core.USBError:
                    pass
                time.sleep(0.5)

        except Exception as e:
            self.log(f"Error: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PortalInspector(root)
    root.mainloop()