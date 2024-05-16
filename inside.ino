#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// Thông tin mạng WiFi
/*const char* ssid = "Jerusalem";
const char* password = "tamsotam";*/
const char* ssid = "TOANZDRAGON";
const char* password = "55555555";
//const char* ssid = "ESP";
//const char* password = "12345678";

// Thông tin máy chủ MQTT
const char* mqtt_server = "192.168.18.217";
const int mqtt_port = 1883;
const char* mqtt_user = "MQTT_mosquitto";

#define DHTPIN D5

// Initialize the DHT object
//DHT dht(DHTPIN, DHT11);

// Initialize the PubSubClient object
WiFiClient espClient;
PubSubClient client(espClient);

float temperature, humidity;
unsigned long pre_mil = 0;
unsigned long interval = 5000;  // Chu kỳ gửi dữ liệu data 0 -> 100s
bool check = 0;
void callback(char* topic, byte* payload, unsigned int length);

void setup() {
  Serial.begin(115200);
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.print("Connected to WiFi: ");
  Serial.println(WiFi.localIP());

  // Set up MQTT server
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  //dht.begin();

  pinMode(D2, OUTPUT);
  pinMode(D6, INPUT);
}
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Read value from DHT sensor
  /*humidity = dht.readHumidity();
  temperature = dht.readTemperature();*/
  humidity = random(20, 100);
  temperature = random(10, 40);
  unsigned long cur_mil = millis();
  // Check if the closing data from the sensor is correct?
  /*if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor");
    return;
  }*/
  char msg[50];
  // Send temperature and humidity data to the MQTT server
  if (cur_mil - pre_mil >= interval) {
    pre_mil = cur_mil;
    snprintf(msg, sizeof(msg), "{\n\"temperature\": %.1f,\n\"humidity\": %.1f\n}", temperature, humidity);
    client.publish("indoor/DHT11/data", msg);
    Serial.print(temperature);
    Serial.print("     ");
    Serial.println(humidity);

    bool gpioValue = digitalRead(D2);
    String payload = "{\"switch_state\": \"" + String(gpioValue ? "True" : "False") + "\"}";
    client.publish("indoor/switch/data", payload.c_str());
  }
  if (digitalRead(D6) == 0) {
    digitalWrite(D2, HIGH);
    check = 1;
  } else if (digitalRead(D6) == 1 && check == 1) {
    digitalWrite(D2, LOW);
    check = 0;
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.println("Message arrived in topic: " + String(topic));

  if (String(topic) == "indoor/switch/control") {
    String msg = "";
    for (int i = 0; i < length; i++) {
      msg += (char)payload[i];
    }
    if (msg == "ON" && check == 0) {
      Serial.println("Turning Switch ON");
      check = 0;
      digitalWrite(D2, HIGH);
    } else if (msg == "OFF" && check == 0) {
      Serial.println("Turning Switch OFF");
      digitalWrite(D2, LOW);
      check = 0;
    }
  } else if (String(topic) == "indoor/interval") {
    String msg = "";
    for (int i = 0; i < length; i++) {
      msg += (char)payload[i];
    }
    interval = msg.toInt();
    Serial.print("Interval: ");
    Serial.print(interval);
    Serial.println("ms");
  } else if (String(topic) == "indoor/switch/control_dis") {
    String msg = "";
    for (int i = 0; i < length; i++) {
      msg += (char)payload[i];
    }
    if (msg == "ON") {
      Serial.println("Turning Switch ON");
      check = 0;
      digitalWrite(D2, HIGH);
    } else if (msg == "OFF") {
      Serial.println("Turning Switch OFF");
      digitalWrite(D2, LOW);
      check = 0;
    }
  }
}
// Check connection to MQTT server and retry connection if connection is sufficient
void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT server...");
    if (client.connect("ESP8266Client")) {
      Serial.println("connected");
      client.subscribe("indoor/interval");
      client.subscribe("indoor/switch/control");
      client.subscribe("indoor/switch/control_dis");

    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}
