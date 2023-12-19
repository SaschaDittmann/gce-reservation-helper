from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time
import os

from google.cloud import compute_v1

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Get environment variables
project_id = os.getenv('PROJECT_ID')
zone = os.getenv('ZONE')
reservation_id = os.getenv('RESERVATION_ID')
target_vm_count = int(os.getenv('TARGET_VM_COUNT', 1))
machine_type = os.getenv('MACHINE_TYPE')

client = compute_v1.ReservationsClient()
current_vm_count = 0

host_name = os.getenv('HOST_NAME', '0.0.0.0')
server_port = int(os.getenv('PORT', '8080'))

class InfoWebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>GCE Reservation Helper</title></head>", "utf-8"))
        self.wfile.write(bytes("<body><p>", "utf-8"))
        self.wfile.write(bytes(f"Reservation ID: {reservation_id}<br/>", "utf-8"))
        self.wfile.write(bytes(f"Zone: {zone}<br/>", "utf-8"))
        self.wfile.write(bytes(f"VM Count: {current_vm_count} / {target_vm_count}<br/>", "utf-8"))
        self.wfile.write(bytes("</p></body></html>", "utf-8"))

def get_current_vm_count():
    """
    Retrieves the current count of virtual machines (VMs) for a reservation.

    Returns:
        int: The current count of VMs for the reservation.

    Raises:
        Exception: If there is an error retrieving the current VM count.
    """
    try:
        global current_vm_count

        request = compute_v1.GetReservationRequest(
            project = project_id,
            zone = zone,
            reservation=reservation_id
        )
        response = client.get(request=request)

        current_vm_count = response.specific_reservation.count
    except Exception as e:
        print("Error getting current VM count")
        print(e)

def create_new_reservation():
    """
    Creates a new reservation in Google Cloud Platform.

    Args:
        None

    Returns:
        None

    Raises:
        Exception: If there is an error creating the reservation.
    """
    try:
        request = compute_v1.InsertReservationRequest(
            project = project_id,
            zone = zone,
            reservation_resource = compute_v1.Reservation(
                name = reservation_id,

                specific_reservation = compute_v1.AllocationSpecificSKUReservation(
                    count = 1,
                    instance_properties = compute_v1.AllocationSpecificSKUAllocationReservedInstanceProperties(
                        machine_type = machine_type,
                    )
                ) 
            )
        )

        # Make the request
        response = client.insert(request=request)

        # Handle the response
        print(response)
    except Exception as e:
        print("Error creating reservation")
        print(e)
    
def resize_reservation():
    """
    Resizes the reservation by increasing the specific SKU count by 1.

    Raises:
        Exception: If there is an error resizing the reservation.
    """
    try:
        request = compute_v1.ResizeReservationRequest(
            project = project_id,
            zone = zone,
            reservation = reservation_id,
            reservations_resize_request_resource = compute_v1.ReservationsResizeRequest(
                specific_sku_count = current_vm_count + 1
            )
        )

        # Make the request
        response = client.resize(request=request)

        # Handle the response
        print(response)
    except Exception as e:
        print("Error resizing reservation")
        print(e)

def reservation_worker():
    """
    Function that manages the creation and resizing of reservations for virtual machines.

    The function continuously checks the current number of virtual machines and compares it to the target number.
    If the current count is zero, a new reservation is created.
    If the current count is less than the target count, the reservation is resized.
    The function sleeps for 30 seconds after each operation.
    """
    while current_vm_count < target_vm_count:
        get_current_vm_count()
        print("Current VM count: " + str(current_vm_count))
        if (current_vm_count == 0):
            print("Creating new reservation...")
            create_new_reservation()
            time.sleep(30)
        else:
            if (current_vm_count < target_vm_count):
                print("Resizing reservation...")
                resize_reservation()
                time.sleep(30)
    print("Target VM Count reached. Exiting...")

if __name__ == '__main__':
    print("Starting reservation worker...")
    thread = threading.Thread(target=reservation_worker)
    thread.start()

    web_server = HTTPServer((host_name, server_port), InfoWebServer)
    print("Server started http://%s:%s" % (host_name, server_port))

    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        pass

    web_server.server_close()
    print("Server stopped.")