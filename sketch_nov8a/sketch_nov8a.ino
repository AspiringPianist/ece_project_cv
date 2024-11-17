#define BUTTON 4
#include <WebServer.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <WiFiClient.h>

const char* ssid = "Network";
const char* password = "qwertyui";
char* hostname = "UNVICTUS.local";  // Default hostname
WebServer server(80);
bool button_pressed = false;
WiFiClient client;  // Declare client globally

// Ultrasonic sensor pins
const int TRIG_PIN_LEFT = 5;    
const int ECHO_PIN_LEFT = 18;   
const int TRIG_PIN_RIGHT = 19;  
const int ECHO_PIN_RIGHT = 21;  

float getDistance(int trigPin, int echoPin) {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    float duration = pulseIn(echoPin, HIGH);
    float distance = duration * 0.0171;  // Convert to centimeters

    return (distance < 1) ? -1 : distance;
}

void handleSensorData() {
    float distanceLeft = getDistance(TRIG_PIN_LEFT, ECHO_PIN_LEFT);
    float distanceRight = getDistance(TRIG_PIN_RIGHT, ECHO_PIN_RIGHT);
    String response = "{\"left\":" + String(distanceLeft) + ",\"right\":" + String(distanceRight) + "}";
    server.send(200, "application/json", response);
}

void getButtonStatus() {
    if (digitalRead(BUTTON) == LOW && !button_pressed) {
        delay(50);  
        if (digitalRead(BUTTON) == LOW) {  
            button_pressed = true;  
            server.send(200, "text/plain", "pressed");
            return;
        }
    } else if (digitalRead(BUTTON) == HIGH && button_pressed) {
        button_pressed = false;
    }
    server.send(200, "text/plain", "not pressed");
}

void setup() {
    Serial.begin(115200);
    
    // Initialize pins
    pinMode(BUTTON, INPUT_PULLUP);
    pinMode(TRIG_PIN_LEFT, OUTPUT);
    pinMode(ECHO_PIN_LEFT, INPUT);
    pinMode(TRIG_PIN_RIGHT, OUTPUT);
    pinMode(ECHO_PIN_RIGHT, INPUT);

    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println(" connected");

    if (!MDNS.begin("esp32")) {
        Serial.println("Error setting up MDNS responder!");
        while(1) {
            delay(1000);
        }
    }
    Serial.println("mDNS responder started");

    // Set up server endpoints
    server.on("/getButtonStatus", getButtonStatus);
    server.begin();
    
    Serial.println("Server started at: ");
    Serial.println(WiFi.localIP());

    // Try to connect to raspberrypi.local
    if(client.connect("raspberrypi.local", 4443)) {
        hostname = "raspberrypi.local";
        Serial.println("Connected to raspberrypi.local");
    }
}

void loop() {
    float distanceLeft = getDistance(TRIG_PIN_LEFT, ECHO_PIN_LEFT);
    float distanceRight = getDistance(TRIG_PIN_RIGHT, ECHO_PIN_RIGHT);
    
    if (distanceLeft > 0 && distanceRight > 0) {
        String response = "{\"left\":" + String(distanceLeft) + ",\"right\":" + String(distanceRight) + "}";
        Serial.println(response);  // For debugging
        
        if (client.connect(hostname, 4443)) {
            client.println("POST / HTTP/1.1");
            client.println("Host: " + String(hostname));
            client.println("Content-Type: application/json");
            client.print("Content-Length: ");
            client.println(response.length());
            client.println();
            client.println(response);
            client.stop();
        }
    }
    
    server.handleClient();
    delay(10);
}
