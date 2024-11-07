// ESP32 Code (main.cpp)
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Define UUIDs
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// Ultrasonic sensor pins
const int TRIG_PIN_LEFT = 5;   // GPIO5
const int ECHO_PIN_LEFT = 18;  // GPIO18
const int TRIG_PIN_RIGHT = 17; // GPIO17
const int ECHO_PIN_RIGHT = 16; // GPIO16

// Global variables
BLEServer *pServer = NULL;
BLECharacteristic *pCharacteristic = NULL;
bool deviceConnected = false;

// Variables for averaging readings
const int NUM_READINGS = 5;
float readingsLeft[NUM_READINGS];
float readingsRight[NUM_READINGS];
int readIndex = 0;
float totalReadingsLeft = 0;
float totalReadingsRight = 0;
float averageDistanceLeft = 0;
float averageDistanceRight = 0;

// Variables for data sending control
unsigned long lastSendTime = 0;
const int SEND_INTERVAL = 50;  // Send every 50ms for more responsive audio

// Server callbacks remain the same as in previous code
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Device connected");
    }

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Device disconnected");
      pServer->startAdvertising();
    }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      std::string rxValue = pCharacteristic->getValue();
      if (rxValue.length() > 0) {
        Serial.println("Received from RPi:");
        Serial.println(rxValue.c_str());
        if (rxValue == "getSingle") {
          sendSingleReading();
        }
      }
    }
};

float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  float duration = pulseIn(echoPin, HIGH);
  float distance = duration * 0.0171;
  
  if (distance > 400 || distance < 2) {
    return -1;
  }
  
  return distance;
}

void updateAverages(float distanceLeft, float distanceRight) {
  // Update left sensor average
  totalReadingsLeft = totalReadingsLeft - readingsLeft[readIndex];
  readingsLeft[readIndex] = distanceLeft;
  totalReadingsLeft = totalReadingsLeft + distanceLeft;
  
  // Update right sensor average
  totalReadingsRight = totalReadingsRight - readingsRight[readIndex];
  readingsRight[readIndex] = distanceRight;
  totalReadingsRight = totalReadingsRight + distanceRight;
  
  // Advance index
  readIndex = (readIndex + 1) % NUM_READINGS;
  
  // Calculate averages
  averageDistanceLeft = totalReadingsLeft / NUM_READINGS;
  averageDistanceRight = totalReadingsRight / NUM_READINGS;
}

void sendSingleReading() {
  float distanceLeft = getDistance(TRIG_PIN_LEFT, ECHO_PIN_LEFT);
  float distanceRight = getDistance(TRIG_PIN_RIGHT, ECHO_PIN_RIGHT);
  
  if (distanceLeft > 0 && distanceRight > 0) {
    char data[100];
    snprintf(data, sizeof(data), 
             "{\"left\":%.2f,\"avgL\":%.2f,\"right\":%.2f,\"avgR\":%.2f}", 
             distanceLeft, averageDistanceLeft, 
             distanceRight, averageDistanceRight);
    pCharacteristic->setValue(data);
    pCharacteristic->notify();
    Serial.printf("Sent: %s\n", data);
  }
}

void setup() {
  Serial.begin(115200);
  
  // Initialize sensor pins
  pinMode(TRIG_PIN_LEFT, OUTPUT);
  pinMode(ECHO_PIN_LEFT, INPUT);
  pinMode(TRIG_PIN_RIGHT, OUTPUT);
  pinMode(ECHO_PIN_RIGHT, INPUT);
  
  // Initialize readings arrays
  for (int i = 0; i < NUM_READINGS; i++) {
    readingsLeft[i] = 0;
    readingsRight[i] = 0;
  }
  
  // Create BLE Device
  BLEDevice::init("ESP32-STEREO-US");
  
  // Create BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());
  
  // Create BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);
  
  // Create BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
                    
  pCharacteristic->setCallbacks(new MyCallbacks());
  pCharacteristic->addDescriptor(new BLE2902());
  
  // Start the service
  pService->start();
  
  // Start advertising
  pServer->getAdvertising()->start();
  Serial.println("BLE device ready");
}

void loop() {
  if (deviceConnected) {
    unsigned long currentTime = millis();
    
    if (currentTime - lastSendTime >= SEND_INTERVAL) {
      float distanceLeft = getDistance(TRIG_PIN_LEFT, ECHO_PIN_LEFT);
      float distanceRight = getDistance(TRIG_PIN_RIGHT, ECHO_PIN_RIGHT);
      
      if (distanceLeft > 0 && distanceRight > 0) {
        updateAverages(distanceLeft, distanceRight);
        
        char data[100];
        snprintf(data, sizeof(data), 
                 "{\"left\":%.2f,\"avgL\":%.2f,\"right\":%.2f,\"avgR\":%.2f}", 
                 distanceLeft, averageDistanceLeft, 
                 distanceRight, averageDistanceRight);
        pCharacteristic->setValue(data);
        pCharacteristic->notify();
        Serial.printf("Sent: %s\n", data);
      }
      
      lastSendTime = currentTime;
    }
  }
  delay(10);
}
