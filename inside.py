import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import threading
import socket
import asyncio

THINGSBOARD_HOST = "thingsboard.hust-2slab.org"
ACCESS_TOKEN = "QkYNlFupK9Gt1FnQ4tjz"
#MQTT_BROKER_HOST = "192.168.4.3"
MQTT_BROKER_HOST = "192.168.192.217"
client_mos = mqtt.Client()
client_tb = mqtt.Client()
client_tb.username_pw_set(ACCESS_TOKEN)
connect = 0
thingsboard_connected = False
temperature_threshold = 35
lock = threading.Lock()
temper = 0
lock = asyncio.Lock()

async def check_internet_connection():
    global connect
    global thingsboard_connected
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            print("Connected to the internet.")
            connect = 1
            await try_connect_to_thingsboard()
        except socket.error:
            print("Disconnected: No internet connection.")
            connect = 0
            thingsboard_connected = False  

            '''# Disconnect and attempt to reconnect the MQTT client
            client_mos.disconnect()
            client_mos.reconnect()'''
        await asyncio.sleep(5)

async def try_connect_to_thingsboard():
    global thingsboard_connected
    try:
        if connect == 1:
            client_tb.on_connect = on_connect_tb
            client_tb.on_message = on_message_tb
            client_tb.connect(THINGSBOARD_HOST, 1883, 60)
            client_tb.loop_start()
            thingsboard_connected = True
    except Exception as e:
        print(f"Failed to connect to ThingsBoard: {e}")

def on_connect_tb(client, userdata, flags, rc):
    if rc == 0:
        #print(f"Connected to ThingsBoard with result code {rc}")
        client_tb.subscribe("v1/devices/me/rpc/request/+")

def on_message_tb(client, userdata, msg):
    payload_tb = json.loads(msg.payload)
    print(f"Received message on ThingsBoard topic {msg.topic}: {payload_tb}")
    if msg.topic.startswith("v1/devices/me/rpc/request/"):
        handle_rpc_request(payload_tb)

def on_connect_mos(client, userdata, flags, rc):
    if rc == 0:
        client_mos.subscribe("indoor/DHT11/data")
        client_mos.subscribe("indoor/switch/data")
    else:
        print(f"Failed to connect to Mosquitto with result code {rc}")
def on_message_mos(client, userdata, msg):
    global thingsboard_connected
    global temperature_threshold
    global temper
    payload_mos = json.loads(msg.payload)
    print(f"Received message on Mosquitto topic {msg.topic}: {payload_mos}")

    if msg.topic == "indoor/DHT11/data":
        temper = payload_mos["temperature"]

        if thingsboard_connected:
            if temper > temperature_threshold:
                send_to_mosquitto_Home_control_dis("OFF")
            send_to_thingsboard(payload_mos["temperature"], payload_mos["humidity"])
    if msg.topic == "indoor/switch/data":
        switch_state = payload_mos.get("switch_state")
        if switch_state is not None and thingsboard_connected:
            send_to_tb(switch_state)
def send_to_thingsboard(temperature, humidity):
    topic = "v1/devices/me/telemetry"
    payload = {
        "temperature": temperature,
        "humidity": humidity
    }
    publish.single(topic, json.dumps(payload), hostname=THINGSBOARD_HOST, port=1883, auth={'username': ACCESS_TOKEN})

def send_to_tb(switch_state):
    topic = "v1/devices/me/attributes"
    if (switch_state == "True"):
        data = {
            "switch_state": True
        }
    else:
        data = {
            "switch_state": False
        }
    publish.single(topic, json.dumps(data), hostname=THINGSBOARD_HOST, port=1883, auth={'username': ACCESS_TOKEN})

def handle_rpc_request(payload):
    method = payload.get("method")
    params = payload.get("params")
    global temperature_threshold
    if method == "setSwitchValue":
        if params is not None:
            if params:
                send_to_mosquitto_Home_control("ON")
            else:
                send_to_mosquitto_Home_control("OFF")
    elif method == "setInSwitchValue":
        if params is not None:
            try:
                
                if 0 <= params <= 100.00:
                    set_interval_Home(params * 1000)
                else:
                    print(f"{params} is not between 0.00 and 100.00")
            except ValueError:
                print("Params are not real numbers.")
    elif method == "setInTempValue":
        if params is not None:
            try:
                
                if 0 <= params <= 100.00:
                    temperature_threshold = params
                    set_Temp_Home(params)
                    print(f"Temperature threshold: ",temperature_threshold)
                else:
                    print(f"{params} is not between 0.00 and 100.00")
            except ValueError:
                print("Params are not real numbers.")

def send_to_mosquitto_Home_control(status):
    mosquitto_topic = "indoor/switch/control"
    payload = status
    publish.single(mosquitto_topic, payload, hostname=MQTT_BROKER_HOST, port=1883)
def send_to_mosquitto_Home_control_dis(status):
    mosquitto_topic = "indoor/switch/control_dis"
    payload = status
    publish.single(mosquitto_topic, payload, hostname=MQTT_BROKER_HOST, port=1883)

def set_interval_Home(value):
    mosquitto_topic = "indoor/interval"
    payload = str(value)
    publish.single(mosquitto_topic, payload, hostname=MQTT_BROKER_HOST, port=1883)
def set_Temp_Home(value):
    mosquitto_topic = "indoor/temp_threshold"
    payload = str(value)
    publish.single(mosquitto_topic, payload, hostname=MQTT_BROKER_HOST, port=1883)
async def main():
    global connect
    global temper

    # Bắt đầu luồng kiểm tra internet
    internet_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(internet_loop)
    internet_task = asyncio.create_task(check_internet_connection())

    client_mos.on_connect = on_connect_mos
    client_mos.on_message = on_message_mos
    client_mos.connect(MQTT_BROKER_HOST, 1883, 60)
    client_mos.loop_start()
    try:
        while True:
            if connect == 1:
                await try_connect_to_thingsboard()
                await asyncio.sleep(5)
            else:
                if not client_mos.is_connected():
                    print("Reconnecting to Mosquitto...")
                    client_mos.reconnect()
                if temper > temperature_threshold:
                    send_to_mosquitto_Home_control_dis("OFF")
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("Server stopped by user.")
    finally:
        internet_task.cancel()
        client_mos.disconnect()
        client_tb.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
