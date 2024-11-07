#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h> //REVIEW

#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"

//REVIEW
// Add these with other defines
#define BUTTON 12  // GPIO12 for the button
#define SERVER_PORT 4443

// Replace with your network credentials
const char* ssid = "Network";
const char* password = "qwertyui";

//REVIEW
String serverAddress;
bool lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

WebServer server(80);

// Define the flash LED pin
#define FLASH_LED_PIN 4

void handleCapture() {
  // Turn on flash
  digitalWrite(FLASH_LED_PIN, HIGH);
  delay(100); // Small delay to allow flash to brighten up

  // Capture the image
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    server.send(500, "text/plain", "Camera capture failed");

    // Turn off flash if capture failed
    digitalWrite(FLASH_LED_PIN, LOW);
    return;
  }

  // Send image to the client
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.send(200, "image/jpeg", String((char*)fb->buf, fb->len));

  // Return the frame buffer and turn off the flash
  esp_camera_fb_return(fb);
  digitalWrite(FLASH_LED_PIN, LOW);
}

void sendUltrasonicData() {

}

// REVIEW
void sendOCRRequest() {
    HTTPClient http;
    String url = "http://" + serverAddress + ":" + String(SERVER_PORT) + "/ocr_button";
    
    http.begin(url);
    int httpResponseCode = http.POST("");
    
    if (httpResponseCode > 0) {
        Serial.printf("OCR request sent. Response code: %d\n", httpResponseCode);
    } else {
        Serial.printf("Error sending OCR request: %d\n", httpResponseCode);
    }
    
    http.end();
}

void setup() {
  Serial.begin(115200);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_HD;
  config.pixel_format = PIXFORMAT_JPEG;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 5;
  config.fb_count = 1;

  if (psramFound()) {
    config.jpeg_quality = 5;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_HD;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Camera sensor settings
  sensor_t *s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);
    s->set_brightness(s, 1);
    s->set_saturation(s, -2);
  }
  s->set_framesize(s, FRAMESIZE_QVGA);

  // Set up WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" connected");

  // REVIEW
  serverAddress = WiFi.localIP().toString();
  pinMode(BUTTON, INPUT_PULLUP);

  // Initialize flash pin as output
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW); // Make sure flash is off initially

  // Set up web server
  server.on("/capture", handleCapture);
  server.begin();

  Serial.print("Camera Ready! Access http://");
  Serial.print(WiFi.localIP());
  Serial.println("/capture to receive an image.");
}

void loop() {
  server.handleClient();
  // Button handling with debounce
    int reading = digitalRead(BUTTON);
    
    if (reading != lastButtonState) {
        lastDebounceTime = millis();
    }
    
    if ((millis() - lastDebounceTime) > debounceDelay) {
        if (reading == LOW) {  // Button pressed (LOW because of INPUT_PULLUP)
            sendOCRRequest();
            while(digitalRead(BUTTON) == LOW) {
                delay(10);  // Wait for button release
            }
        }
    }
    
    lastButtonState = reading;
}
