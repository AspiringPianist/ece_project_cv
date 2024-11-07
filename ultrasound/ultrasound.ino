#include <WiFi.h>

// Wi-Fi credentials
const char* ssid = "Network";       // Replace with your mobile hotspot SSID
const char* password = "qwertyui";  // Replace with your mobile hotspot password

// Server details
const char* serverIP = "192.168.63.4";  // Replace with your desktop's IP address
const int serverPort = 4443;            // Ensure this matches your Python server

// Ultrasonic sensor pins
const int TRIG_PIN_LEFT = 5;    // GPIO5
const int ECHO_PIN_LEFT = 18;   // GPIO18
const int TRIG_PIN_RIGHT = 19;  // GPIO17
const int ECHO_PIN_RIGHT = 21;  // GPIO16

void setup() {
  Serial.begin(115200);

  // Initialize sensor pins
  pinMode(TRIG_PIN_LEFT, OUTPUT);
  pinMode(ECHO_PIN_LEFT, INPUT);
  pinMode(TRIG_PIN_RIGHT, OUTPUT);
  pinMode(ECHO_PIN_RIGHT, INPUT);

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
}

float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  float duration = pulseIn(echoPin, HIGH);
  float distance = duration * 0.0171;  // Convert to centimeters

  // Validate the distance and return -1 if out of range
  if (distance < 1) {
    return -1;  // Invalid distance
  }

  return distance;
}

void loop() {
  // Get distance readings from both sensors
  float distanceLeft = getDistance(TRIG_PIN_LEFT, ECHO_PIN_LEFT);
  float distanceRight = getDistance(TRIG_PIN_RIGHT, ECHO_PIN_RIGHT);

  // Only send data if both distances are valid
  if (distanceLeft > 0 && distanceRight > 0) {
    // Create HTTP client
    WiFiClient client;
    if (client.connect(serverIP, serverPort)) {
      // Construct the HTTP POST request
      String postData = "left=" + String(distanceLeft) + "&right=" + String(distanceRight);
      client.print(String("POST / HTTP/1.1\r\n") + "Host: " + serverIP + "\r\n" + "Connection: close\r\n" + "Content-Type: application/x-www-form-urlencoded\r\n" + "Content-Length: " + postData.length() + "\r\n\r\n" + postData);
      Serial.printf("Sent: %s\n", postData.c_str());

      // Wait for the response from the server
      while (client.available()) {
        String line = client.readStringUntil('\n');
        Serial.println(line);
      }
    } else {
      Serial.println("Error in HTTP request: connection refused");
    }
  } else {
    Serial.println("Invalid distance readings");  // Report invalid readings
  }

  delay(100);  // Adjust the delay as necessary
}