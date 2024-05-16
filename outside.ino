#include <SPI.h>
#include <Dhcp.h>
#include <Dns.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <coap-simple.h>
#include <DHT.h>
#define LEDP D2

const char* ssid = "TOANZDRAGON";
const char* password = "55555555";
const int coapPort = 5684; // Default CoAP port
const String resourcePath = "dht11";
#define DHTPIN D5  // Sử dụng chân GPIO2
unsigned long pre_mil = 0;   // Biến lưu trữ thời điểm gửi dữ liệu gần nhất
bool check=0;
int interval=5000;
int ledstate;
int count=30;
IPAddress serverip=IPAddress(192, 168, 192, 217);
// Khởi tạo đối tượng DHT
//DHT dht(DHTPIN, DHT11);
float temperature;
float humidity;
// LED STATE
bool LEDSTATE;
// CoAP client response callback
void callback_response(CoapPacket &packet, IPAddress ip, int port);

// CoAP server endpoint url callback
void callback_light(CoapPacket &packet, IPAddress ip, int port);

void callback_interval(CoapPacket &packet, IPAddress ip, int port) ;
// UDP and CoAP class
WiFiUDP udp;
Coap coap(udp);



void callback_interval(CoapPacket &packet, IPAddress ip, int port) {
  
  // send response
  char p[packet.payloadlen + 1];
  memcpy(p, packet.payload, packet.payloadlen);
  p[packet.payloadlen] = NULL;
  
  String message(p);
  interval = message.toInt();
  Serial.print("Interval: ");
    Serial.print(interval);
    Serial.println("ms");
  coap.sendResponse(ip,port, packet.messageid ,"1", 1, COAP_CONTENT , COAP_TEXT_PLAIN, packet.token, packet.tokenlen);
}
// CoAP server endpoint URL
void callback_light(CoapPacket &packet, IPAddress ip, int port) {
  Serial.println("[led] ON/OFF");
  
  // send response
  char p[packet.payloadlen + 1];
  memcpy(p, packet.payload, packet.payloadlen);
  p[packet.payloadlen] = NULL;
  
  String message(p);
  Serial.println(message);

  if (message.equals("0") && check==0){
    check=0;
    LEDSTATE = false;}
  else if(message.equals("1") && check==0){
    LEDSTATE = true;
    check=0;}
  if (LEDSTATE) {
    digitalWrite(LEDP, HIGH) ; 
    Serial.println("ON");
   coap.sendResponse(ip,port, packet.messageid ,"1", 1, COAP_CONTENT , COAP_TEXT_PLAIN, packet.token, packet.tokenlen);
  } else { 
    digitalWrite(LEDP, LOW) ; 
    Serial.println("OFF");
    coap.sendResponse(ip,port, packet.messageid ,"0", 1, COAP_CONTENT , COAP_TEXT_PLAIN,packet.token, packet.tokenlen);
  }
}

// CoAP client response callback
void callback_response(CoapPacket &packet, IPAddress ip, int port) {
  //Serial.println("[Coap Response got]");
  serverip=ip;

}

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }

  //Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

 //dht.begin();
  // LED State
   pinMode(LEDP, OUTPUT);
  digitalWrite(LEDP, LOW);
  pinMode(D6,INPUT);
  LEDSTATE = true;
  
  
  Serial.println("Setup Callback Light");
  coap.server(callback_light, "led");

  // client response callback.
  // this endpoint is single callback.
  Serial.println("Setup Response Callback");
  coap.response(callback_response);

 Serial.println("Setup Callback Interval");
  coap.server(callback_interval, "interval");

  // start coap server/client
  coap.start();
}

void loop() {
  ledstate=digitalRead(LEDP);
   unsigned long cur_mil = millis();
   
  humidity=random(20,100);
  temperature=random(10,40);
  

 if (ledstate == 1) {
    count = count - 2;
    //Serial.println(count);
    if (count <= 0) {
        digitalWrite(LEDP, LOW);
        count = 30;
        Serial.println("Pump control is off (time on >30s)");
        
    }}
 else if (ledstate == 0) {
    count = 30;
}
  char msg[100];
  char state[50];
  if (cur_mil - pre_mil >= (interval-1000)){ 
   //Serial.println(interval-3100);{
    //Serial.println(cur_mil - pre_mil);
    pre_mil = cur_mil;
  snprintf(msg, sizeof(msg), "{\n\"temperature\": %.1f,\n\"humidity\": %.1f}", temperature, humidity);
Serial.print("temperature: ");  
Serial.print(temperature, 1);  // In số thập phân với 1 chữ số sau dấu chấm
Serial.print(", humidity: ");
Serial.print(humidity, 1);     // In số thập phân với 1 chữ số sau dấu chấm
Serial.println();
  // Send CoAP PUT request to update the dht11 resource
  coap.put(serverip, coapPort, resourcePath.c_str(), msg);}
  delay(200);
  snprintf(state, sizeof(state), "{\n\"ledstate\": %d}", ledstate);
  coap.put(serverip, coapPort,"state", state);
  //Serial.println(serverip);
  delay(200);

   if(digitalRead(D6)==0) {
    digitalWrite(D2,HIGH);
    check = 1;
  }
  else if (digitalRead(D6)==1 && check == 1) {
    digitalWrite(D2,LOW);
    check = 0;
  }

 // printf("%d", msgid_2);
  delay(600);
  coap.loop();
}

