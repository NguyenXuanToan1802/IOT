import asyncio
import json
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import aiocoap.resource as resource
import aiocoap
import aiocoap.options
import logging
import threading
import socket

# Global variables
connect = 0
thingsboard_connected = False
temper = 0
maxtemper = 35
client_tb = mqtt.Client()
client_tb.username_pw_set("UPLF57IeY3sqSTrsp60n")
pumpstate = False

async def check_internet_connection(loop):
    """
    Periodically checks internet connection.
    """
    global connect
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            print("Connected to the internet.")
            connect = 1
        except socket.error:
            print("Disconnected: No internet connection.")
            connect = 0
        await asyncio.sleep(10)

async def set_interval_Home(interval):
    """
    Sets the interval via CoAP to ESP8266.
    """
    esp8266_ip = "192.168.192.204"
    esp8266_port = 5683
    path = "interval"
    interval = round(interval)
    uri = f"coap://{esp8266_ip}:{esp8266_port}/{path}"
    payload = str(interval)
    print(payload)
    try:
        request = aiocoap.Message(code=aiocoap.PUT, uri=uri, payload=payload.encode('utf-8'))
        context = await aiocoap.Context.create_client_context()
        response = await context.request(request).response
        print(f"Interval sent to ESP8266 {response.payload}")
    except Exception as e:
        print(f"Failed to send interval to ESP8266: {e}")

async def send_to_esp8266(led_status):
    """
    Sends request to ESP8266 to control the pump.
    """
    esp8266_ip = "192.168.192.204"
    esp8266_port = 5683
    led_path = "led"
    global pumpstate
    uri = f"coap://{esp8266_ip}:{esp8266_port}/{led_path}"
    pumpstate = led_status
    payload = "1" if led_status else "0"
    try:
        request = aiocoap.Message(code=aiocoap.PUT, uri=uri, payload=payload.encode('utf-8'))
        context = await aiocoap.Context.create_client_context()
        response = await context.request(request).response
        if led_status:
            print(f"Request sent to ESP8266: Pumpcontrol ON")
        else:
            print(f"Request sent to ESP8266: Pumpcontrol OFF")
    except Exception as e:
        print(f"Failed to send request to ESP8266: {e}")

class DHT11Resource(resource.Resource):
    """
    CoAP resource for handling sensor data.
    """
    def __init__(self):
        super().__init__()

    async def render_put(self, request):
        """
        Handles PUT requests for the DHT11 resource.
        """
        global temper
        payload = request.payload.decode('utf-8')
        data = json.loads(payload)
        print("Received data from ESP8266:", data)
        temper = data.get("temperature")
        if connect == 1:
            await self.send_to_thingsboard(data)
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"Data received successfully", mtype=aiocoap.NON)

    async def send_to_thingsboard(self, data):
        """
        Sends sensor data to ThingsBoard via MQTT.
        """
        mqtt_server = "thingsboard.hust-2slab.org"
        mqtt_port = 1883
        access_token = "UPLF57IeY3sqSTrsp60n"
        topic = "v1/devices/me/telemetry"
        payload = json.dumps({"temperature": data.get("temperature"), "humidity": data.get("humidity")})
        publish.single(topic, payload, hostname=mqtt_server, port=mqtt_port, auth={"username": access_token})

class State(resource.Resource):
    """
    CoAP resource for handling state data.
    """
    def __init__(self):
        super().__init__()

    async def render_put(self, request):
        global temper
        payload = request.payload.decode('utf-8')
        data = json.loads(payload)
        if connect == 1:
            await self.send_state_to_thingsboard(data)
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"Data received successfully", mtype=aiocoap.NON)

    async def send_state_to_thingsboard(self, data):
        mqtt_server = "thingsboard.hust-2slab.org"
        mqtt_port = 1883
        access_token = "UPLF57IeY3sqSTrsp60n"
        topic = "v1/devices/me/attributes"
        if data.get("ledstate") == 1:
            payload = json.dumps({"state": True})
        else:
            payload = json.dumps({"state": False})
        if connect == 1:
            publish.single(topic, payload, hostname=mqtt_server, port=mqtt_port, auth={"username": access_token})
            print("State sent to ThingsBoard:", payload)

async def handle_rpc_request(payload):
    """
    Handles RPC requests from ThingsBoard.
    """
    method = payload.get("method")
    params = payload.get("params")
    global maxtemper
    if method == "setValue":
        if params is not None:
            if params:
                print("ON")
                await send_to_esp8266(True)
            else:
                print("OFF")
                await send_to_esp8266(False)
    elif method == "interval":
        if params is not None:
            try:
                num = float(params)
                if 0 <= num <= 100.00:
                    await set_interval_Home(params * 1000)
                else:
                    print(f"{num} is not between 0.00 and 100.00")
            except ValueError:
                print("Params are not real numbers.")
    elif method == "maxtemper":
        if params is not None:
            try:
                if 0 <= params <= 100.00:
                    maxtemper = params
                    print(f"Temperature threshold: ", maxtemper)
                else:
                    print(f"{params} is not between 0.00 and 100.00")
            except ValueError:
                print("Params are not real numbers.")

def on_connect_tb(client, userdata, flags, rc):
    global thingsboard_connected
    if rc == 0:
        thingsboard_connected = True
        client_tb.subscribe("v1/devices/me/rpc/request/+")
    else:
        thingsboard_connected = False
        print(f"Failed to connect to ThingsBoard with result code {rc}")

def on_message_tb(client, userdata, msg):
    payload_tb = json.loads(msg.payload)
    if msg.topic.startswith("v1/devices/me/rpc/request/"):
        asyncio.run(handle_rpc_request(payload_tb))

async def try_connect_to_thingsboard():
    try:
        client_tb.on_connect = on_connect_tb
        client_tb.on_message = on_message_tb
        client_tb.connect("thingsboard.hust-2slab.org", 1883, 60)
        client_tb.loop_start()
    except Exception as e:
        print(f"Failed to connect to ThingsBoard: {e}")

async def main():
    internet_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(internet_loop)
    internet_thread = threading.Thread(target=lambda: asyncio.run(check_internet_connection(internet_loop)))
    internet_thread.start()

    root = resource.Site()
    root.add_resource(['dht11'], DHT11Resource())
    root.add_resource(['state'], State())
    context = await aiocoap.Context.create_server_context(root, bind=("192.168.192.217", 5684))
    
    try:
        while True:
            if connect == 1:
                await try_connect_to_thingsboard()
                if temper > maxtemper:
                    await send_to_esp8266(True)
                await asyncio.sleep(5)
            else:
                if temper > maxtemper:
                    await send_to_esp8266(True)
                await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("Server stopped by user.")
    finally:
        internet_loop.stop()
        internet_thread.join()
        await context.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
