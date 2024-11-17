import pyttsx3
import requests
from PIL import Image

from ocr import run_ocr

ESP32_IP = ""

def capture_and_process_image():
    # Capture image from ESP32-CAM
    capture_url = f"http://{ESP32_IP}/capture"
    response = requests.get(capture_url)
    
    # Save captured image temporarily
    temp_image_path = "temp_capture.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(response.content)
    
    Image.open(temp_image_path).show()
    # Run OCR using PaddleOCR
    detected_text = run_ocr(temp_image_path)
    
    # Clean up temporary file
    # os.remove(temp_image_path)
    
    # Initialize text-to-speech engine
    engine = pyttsx3.init()
    
    # Print and speak the detected text
    print("Detected text:", detected_text)
    for text in detected_text:
        engine.say(text)
        engine.runAndWait()

def main():
    # while True:
        # Poll the status endpoint to check for button press
        # status_url = f"http://{ESP32_IP}/status"
    try:
        # response = requests.get(status_url)
        # status = response.json()
        
        # You'll need to add a button status field in your ESP32 code
        # if status.get('button_pressed', False):
        capture_and_process_image()
            
    except requests.exceptions.RequestException:
        print("Connection error. Retrying...")
            # continue

if __name__ == "__main__":
    main()
