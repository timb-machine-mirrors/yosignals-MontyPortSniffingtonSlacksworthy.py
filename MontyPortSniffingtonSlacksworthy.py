import socket
import sys
import subprocess
import requests
import time

# Check for required packages and install them if needed
try:
    import dns.resolver
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "dnspython"])
    import dns.resolver

# Set up Slack Webhook
slack_webhook_url = "SLACKWEBHOOK"  # Replace with your webhook URL

# Listening socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = 50050  # Port number to listen on
server_socket.bind(('0.0.0.0', port))
server_socket.listen(1)

def nslookup(ip):
    try:
        result = dns.resolver.resolve_address(ip)
        return result[0].to_text()
    except Exception as e:
        return "Not Found"

def post_to_slack(text):
    payload = {"text": text}

    try:
        response = requests.post(slack_webhook_url, json=payload)
        if response.status_code == 200:
            print("Posted to Slack.")
        else:
            print(f"Error posting to Slack: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print("Error posting to Slack:", e)

# Debounce configuration
debounce_time = 5  # Time in seconds to group events from the same IP address
ip_debounce = {}

while True:
    client_socket, address = server_socket.accept()
    ip = address[0]
    current_time = time.time()

    # If the IP is not in the debounce dictionary or enough time has passed, send a message
    if ip not in ip_debounce or current_time - ip_debounce[ip] >= debounce_time:
        nslookup_result = nslookup(ip)
        message = f"Connection from IP: {ip}\nNSLookup: {nslookup_result}"
        print(message)
        post_to_slack(message)

    # Update the debounce dictionary with the current timestamp for the IP address
    ip_debounce[ip] = current_time

    client_socket.close()