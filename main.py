import os
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Event
from time import sleep

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
host_name = os.getenv('HOST_NAME', '0.0.0.0')
server_port = int(os.getenv('PORT', '8080'))

client = compute_v1.ReservationsClient()
current_vm_count = 0
global_log_fields = {}

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
        current_vm_count = 0

        request = compute_v1.GetReservationRequest(
            project = project_id,
            zone = zone,
            reservation=reservation_id
        )
        response = client.get(request=request)

        current_vm_count = response.specific_reservation.count
    except Exception as e:
        log_error("Error getting current VM count: " + str(e))

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
        result=response.result()
        if result is not None:
            log_error(str(result))
    except Exception as e:
        log_error("Error creating reservation: " + str(e))
    
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
        result=response.result()
        if result is not None:
            log_error(str(result))
    except Exception as e:
        log_error("Error resizing reservation: " + str(e))

def reservation_worker(event: Event) -> None:
    """
    Function that manages the creation and resizing of reservations for virtual machines.

    The function continuously checks the current number of virtual machines and compares it to the target number.
    If the current count is zero, a new reservation is created.
    If the current count is less than the target count, the reservation is resized.
    The function sleeps for 30 seconds after each operation.
    """
    while current_vm_count < target_vm_count:
        get_current_vm_count()
        log_info("Current VM count: " + str(current_vm_count))
        if (current_vm_count == 0):
            log_info("Creating new reservation...")
            create_new_reservation()
            sleep(30)
        else:
            if (current_vm_count < target_vm_count):
                log_info("Resizing reservation...")
                resize_reservation()
                sleep(30)
        if event.is_set():
            log_info('The thread was stopped prematurely.')
            break
    if current_vm_count >= target_vm_count:
        log_info("Target VM Count reached. Exiting...")

def log_info(message: str) -> None:
    """
    Logs an info message to the Google Cloud Logging service.

    Args:
        message (str): The info message to log.

    Returns:
        None
    """
    entry = dict(
        severity="INFO",
        message=message,
        **global_log_fields,
    )

    print(json.dumps(entry))

def log_error(message: str) -> None:
    """
    Logs an error message to the Google Cloud Logging service.

    Args:
        message (str): The error message to log.

    Returns:
        None
    """
    entry = dict(
        severity="ERROR",
        message=message,
        **global_log_fields,
    )

    print(json.dumps(entry), file=sys.stderr)

if __name__ == '__main__':
    log_info("Starting reservation worker...")
    thread_stopping_event = Event()
    thread = Thread(target=reservation_worker, args=(thread_stopping_event,))
    thread.start()

    web_server = HTTPServer((host_name, server_port), InfoWebServer)
    log_info("Server started http://%s:%s" % (host_name, server_port))

    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        pass

    web_server.server_close()
    log_info("Web Server stopped.")

    log_info("Reservation Worker stopping...")
    thread_stopping_event.set()
    thread.join()
    log_info("Reservation Worker stopped.")
