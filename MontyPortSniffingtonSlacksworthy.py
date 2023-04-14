import socket
import sys
import subprocess
import requests
import time
import sqlite3

# Check for required packages and install them if needed
try:
    import dns.resolver
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "dnspython"])
    import dns.resolver

try:
    import whois
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-whois"])
    import whois

try:
    import pytz
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
    import pytz

try:
    import ntplib
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ntplib"])
    import ntplib

try:
    from dateutil import tz
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dateutil"])
    from dateutil import tz

# Set up Slack Webhook
slack_webhook_url = "YOURSLACKWEBHOOK"  # Replace with your webhook URL

# Set up SQLite database
db_name = "connections.db"

conn = sqlite3.connect(db_name)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS connections
             (timestamp REAL, ip TEXT, nslookup TEXT, whois TEXT)''')
conn.commit()

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

def whois_lookup(ip):
    try:
        w = whois.whois(ip)
        whois_string = str(w).replace('\n', ' ').replace('\r', '')
        return whois_string
    except Exception as e:
        return "WHOIS Lookup Failed"

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

def save_to_db(timestamp, ip, nslookup, whois):
    c.execute("INSERT INTO connections (timestamp, ip, nslookup, whois) VALUES (?, ?, ?, ?)",
              (timestamp, ip, nslookup, whois))
    conn.commit()

def get_timezone_and_ntp():
    # Get local timezone
    local_timezone = str(tz.tzlocal())

    # Get NTP server details
    ntp_client = ntplib.NTPClient()
    ntp_server = 'pool.ntp.org'
    try:
        response = ntp_client.request(ntp_server, version=3)
        ntp_time = response.tx_time
    except ntplib.NTPException as e:
        ntp_time = "NTP request failed"

    return local_timezone, ntp_time

# Debounce configuration
debounce_time = 5  # Time in seconds to group events from the same IP address
ip_debounce = {}

while True:

    client_socket, address = server_socket.accept()
    ip = address[0]
    current_time = time.time()
    local_timezone, ntp_time = get_timezone_and_ntp()

 # If the IP is not in the debounce dictionary or enough time has passed, send a message
    if ip not in ip_debounce or current_time - ip_debounce[ip] >= debounce_time:
        nslookup_result = nslookup(ip)
        whois_result = whois_lookup(ip)
        message = f"Timezone: {local_timezone}\nNTP Time: {ntp_time}\nConnection from IP: {ip}\nNSLookup: {nslookup_result}\nWHOIS: {whois_result}"
        print(message)
        post_to_slack(message)
        save_to_db(current_time, ip, nslookup_result, whois_result)

 # Update the debounce dictionary with the current timestamp for the IP address
    ip_debounce[ip] = current_time

    client_socket.close()