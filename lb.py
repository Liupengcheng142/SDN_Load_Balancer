import requests
import time
import logging
import json

from rules import to_wifi


# Create the logger
logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
stream_handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)

# Define global vars
users = []
init_param = {}
stop = False


def run_lb(name):
    """
    Starts the Load Balancer application
    """
    global init_param, stop

    # Read the initial config parameters
    with open('init_config.json') as init_config:
        init_param = json.load(init_config)

    # Check if all the values are not null
    for param, value in init_param.items():
        if not value:
            logger.debug(f"Null initial value for {param} - Waiting to get\
 initial/parameters via API")
            return

    # Initialize the traffic variable
    response = requests.get(url=f"http://{init_param['ryu_ip']}:8080/stats/\
port/{init_param['br-int_dpid']}/{init_param['vlc_of_port']}")
    traffic = response.json()[init_param['br-int_dpid']][0]["rx_bytes"]

    # Start the lb iteration
    while not stop:
        response = requests.get(url=f"http://{init_param['ryu_ip']}:8080/\
stats/port/{init_param['br-int_dpid']}/{init_param['vlc_of_port']}")
        new_traffic = response.json()[init_param['br-int_dpid']][0]["rx_bytes"]
        # Calculate Mbps
        bytes_per_sec = (new_traffic - traffic)/init_param["interval"]
        Mbytes_per_sec = bytes_per_sec/1000000
        bitrate = Mbytes_per_sec * 8
        logger.debug(bitrate)
        if bitrate > init_param["upper_bw_limit"]:
            logger.debug(f"The bitrate is over upper bw limit ({bitrate})")
            logger.debug(users)
        elif bitrate < init_param["lower_bw_limit"]:
            logger.debug(f"The bitrate is under lower bw linit ({bitrate})")
            logger.debug(users)
            wifi_list = get_wifi_users()
            vlc_users = get_vlc_users(wifi_list)
#             if len(users) > 0:
#                 data = json.dumps(to_wifi(init_param, users[0]))
#                 headers = {"Content-Type": "application/json"}
#                 requests.post(url=f"http://{init_param['ryu_ip']}:8080/stats/\
# flowentry/add", data=data, headers=headers)
#                 time.sleep(30)
#                 requests.post(url=f"http://{init_param['ryu_ip']}:8080/stats/\
# flowentry/delete_strict", data=data, headers=headers)
        traffic = new_traffic
        time.sleep(init_param["interval"])

    logger.info(f"Load Balancer on thread {name} stops")


def get_wifi_users():
    """
    Gets the IP of the users currently on the WiFi
    """
    response = requests.get(url=f"http://{init_param['ryu_ip']}:8080/\
stats/flow/{init_param['br-int_dpid']}")
    rules = response.json()[init_param['br-int_dpid']]
    wifi_list = []
    for rule in rules:
        try:
            vlc_ip = rule["match"]["nw_dst"]
        except KeyError:
            continue
        else:
            wifi_list.append(vlc_ip)
        logger.debug(f"WiFi Users: {wifi_list}")
    return wifi_list


def get_vlc_users(wifi_list):
    """
    Returns the list of the users that are currently on the VLC/mmWave
    """
    vlc_users = [user for user in users if user["vlc_ip"] not in wifi_list]
    logger.debug(f"VLC Users: {vlc_users}")
    return vlc_users
