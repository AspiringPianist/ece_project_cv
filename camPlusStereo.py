import csv
import logging
import threading
import time
from collections import deque
from datetime import datetime
from queue import Queue
import json
import matplotlib.pyplot as plt
import netifaces
import numpy as np
import pyttsx3
import requests
import sounddevice as sd
from PIL import Image
from flask import Flask, request
from scipy import signal

# ocr option 1: api ocr that uses ml: from ocr import run_ocr
from google_ocr import run_ocr #ocr option 2: goat gemini ai
# ocr option 3: paddle ocr (worst case)

#Figuring out IPs ----------------------------------------------------------------------
ESP32CAM_IP, ESP32_IP = "esp32cam.local", "esp32.local"
# -------------------------------------------------------------------------------------------------=

last_button_status = None  # Add this outside the function

def capture_and_process_image():
    try:
        # Capture image from ESP32-CAM
        capture_url = f"http://{ESP32CAM_IP}/capture"
        response = requests.get(capture_url)
        # Save captured image temporarily
        temp_image_path = "temp_capture.jpg"
        with open(temp_image_path, "wb") as f:
            f.write(response.content)
        Image.open(temp_image_path).show()
        # Run OCR using PaddleOCR
        detected_text = run_ocr(temp_image_path)
        if detected_text:
            engine = pyttsx3.init()
            # Clean up temporary file
            # os.remove(temp_image_path)
            # Initialize text-to-speech engine
            # Print and speak the detected text
            print("Detected text:", detected_text)
            if(detected_text):
                engine.say(detected_text)
                engine.runAndWait()
        else:
            return
    except requests.exceptions.RequestException as e:
        print(f"Error capturing image: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        
# Initialize Flask app
app = Flask(__name__)

# Audio parameters
SAMPLE_RATE = 44100
BLOCK_SIZE = 2048
FREQ_LEFT = 440   # A4 note for left channel
FREQ_RIGHT = 880  # A5 note for right channel

# Distance to volume mapping parameters
MAX_DISTANCE = 300  # cm
MIN_DISTANCE = 5   # cm

# Data visualization setup
MAX_POINTS = 100
distances_left = deque(maxlen=MAX_POINTS)
distances_right = deque(maxlen=MAX_POINTS)
timestamps = deque(maxlen=MAX_POINTS)

# Global flags and data queue
audio_enabled = True
data_queue = Queue()
# class StereoToneGenerator:
#     def __init__(self):
#         self.stream = sd.OutputStream(
#             channels=2,
#             samplerate=SAMPLE_RATE,
#             blocksize=BLOCK_SIZE,
#             callback=self.audio_callback
#         )
#         self.volume_left = 0
#         self.volume_right = 0
#         self.last_update = time.time()
        
#         # Enhanced frequency separation for better directionality
#         self.left_phase = 0
#         self.right_phase = 0
#         self.left_freq = 1200  # Higher frequency for left
#         self.right_freq = 300  # Lower frequency for right
        
#     def start(self):
#         if not self.stream.active:
#             self.stream.start()
        
#     def stop(self):
#         if self.stream.active:
#             self.stream.stop()
        
#     def _distance_to_volume(self, distance):
#         if distance < MIN_DISTANCE or distance > MAX_DISTANCE:
#             return 0
#         # Sharper volume curve for better distance perception
#         volume = np.exp(-(distance - MIN_DISTANCE) / (MAX_DISTANCE/2.5))
#         return np.clip(volume, 0, 1)  # Increased max volume for clearer cues
        
#     def update_volumes(self, left_dist, right_dist):
#         # Enhanced channel separation
#         self.volume_right = self._distance_to_volume(left_dist)
#         self.volume_left = self._distance_to_volume(right_dist)
#         self.last_update = time.time()
        
#     def audio_callback(self, outdata, frames, time_info, status):
#         t = np.arange(frames) / SAMPLE_RATE
        
#         # Generate tones with enhanced harmonic content
#         left_tone = 0.7 * np.sin(2 * np.pi * self.left_freq * t + self.left_phase) + \
#                    0.3 * np.sin(4 * np.pi * self.left_freq * t + self.left_phase)
#         right_tone = 0.7 * np.sin(2 * np.pi * self.right_freq * t + self.right_phase) + \
#                     0.3 * np.sin(4 * np.pi * self.right_freq * t + self.right_phase)
        
#         # Update phases
#         self.left_phase += 2 * np.pi * self.left_freq * frames / SAMPLE_RATE
#         self.right_phase += 2 * np.pi * self.right_freq * frames / SAMPLE_RATE
        
#         # Apply volume with enhanced stereo separation
#         outdata[:, 1] = left_tone * self.volume_left
#         outdata[:, 0] = right_tone * self.volume_right


class StereoToneGenerator:
    def __init__(self):
        self.stream = sd.OutputStream(
            channels=2,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            callback=self.audio_callback
        )
        self.volume_left = 0
        self.volume_right = 0
        self.last_update = time.time()
        self.audio_duration = 2.0  # Duration to play audio in seconds
        
        # Create bandpass filter
        self.nyquist = SAMPLE_RATE / 2
        self.cutoff_low = 200  # Hz
        self.cutoff_high = 2000  # Hz
        self.order = 4
        
        b, a = signal.butter(self.order, 
                           [self.cutoff_low/self.nyquist, 
                            self.cutoff_high/self.nyquist], 
                           btype='band')
        self.b = b
        self.a = a
        
        # Buffer for filter state
        self.zi_left = signal.lfilter_zi(self.b, self.a)
        self.zi_right = signal.lfilter_zi(self.b, self.a)
        
    def start(self):
        if not self.stream.active:
            self.stream.start()
        
    def stop(self):
        if self.stream.active:
            self.stream.stop()
        
    def update_volumes(self, left_dist, right_dist):
        self.volume_left = self._distance_to_volume(left_dist)
        self.volume_right = self._distance_to_volume(right_dist)
        self.last_update = time.time()  # Reset timer when new readings arrive
        
    def _distance_to_volume(self, distance):
        if distance < MIN_DISTANCE or distance > MAX_DISTANCE:
            return 0
        # Exponential mapping for more natural volume falloff
        volume = np.exp(-(distance - MIN_DISTANCE) / (MAX_DISTANCE/4))
        return np.clip(volume, 0, 1) * 0.3  # Max volume 0.3 to prevent harshness
        
    def audio_callback(self, outdata, frames, time_info, status):
        # Check if audio should be played based on time elapsed
        current_time = time.time()
        if current_time - self.last_update > self.audio_duration:
            outdata.fill(0)
            return
            
        # Generate white noise
        noise = np.random.randn(frames)
        
        # Filter channels
        left_filtered, self.zi_left = signal.lfilter(
            self.b, self.a, noise, zi=self.zi_left * noise[0]
        )
        right_filtered, self.zi_right = signal.lfilter(
            self.b, self.a, noise, zi=self.zi_right * noise[0]
        )
        
        # Apply volume
        outdata[:, 1] = left_filtered * self.volume_left
        outdata[:, 0] = right_filtered * self.volume_right# Initialize audio generator
tone_gen = StereoToneGenerator()
tone_gen.start()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sensor_data.log'),
        logging.StreamHandler()
    ]
)

# CSV setup
csv_filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

def save_to_csv(timestamp, left_dist, right_dist):
    if not hasattr(save_to_csv, "header_written"):
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'left_distance', 'right_distance'])
            save_to_csv.header_written = True
    
    with open(csv_filename, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, left_dist, right_dist])

# def update_plot():
#     plt.clf()
#     plt.plot(list(timestamps), list(distances_left), label='Left Sensor', color='blue')
#     plt.plot(list(timestamps), list(distances_right), label='Right Sensor', color='red')
#     plt.xlabel('Time')
#     plt.ylabel('Distance (cm)')
#     plt.title('Stereo Ultrasonic Sensor Data')
#     plt.legend()
#     plt.grid(True)
#     plt.pause(0.01)  # Increase pause time from 0.01 to 0.1


# def visualization_thread():
#     plt.ion()
#     update_counter = 0
#     while True:
#         if not data_queue.empty():
#             data = data_queue.get()
#             distances_left.append(int(data['left']))
#             distances_right.append(int(data['right']))
#             timestamps.append(data['timestamp'])
#             update_counter += 1
#             if update_counter >= 5:  # Update every 5 data points
#                 update_plot()
#                 update_counter = 0
#         time.sleep(0.1)


def poll_sensor_data():
    while True:
        try:
            # Get sensor data from ESP32
            response = requests.get(f"http://{ESP32_IP}/getSensorData")
            sensor_data = response.json()
            print(sensor_data)
            # Extract distance values from JSON response
            left_distance = float(sensor_data['left'])
            right_distance = float(sensor_data['right'])
            
            # Create timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Update audio if enabled
            if audio_enabled:
                tone_gen.update_volumes(left_distance, right_distance)
            
            # Add data to visualization queue
            data_queue.put({
                'timestamp': timestamp,
                'left': left_distance,
                'right': right_distance
            })
            
            # Save to CSV
            save_to_csv(timestamp, left_distance, right_distance)
            
            # Log the received data
            #logging.info(f"Received - Left: {left_distance}cm, Right: {right_distance}cm")
            
        except Exception as e:
            logging.error(f"Error polling sensor data: {str(e)}")
            
@app.route('/', methods=['POST'])
def receive_data():
    try:
        # Get data from request body
        data = request.get_data().decode('utf-8')
        sensor_data = json.loads(data)
        
        # Extract distance values
        left_distance = float(sensor_data['left'])
        right_distance = float(sensor_data['right'])
        
        # Create timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Update audio if enabled
        if audio_enabled:
            tone_gen.update_volumes(left_distance, right_distance)
        
        # Add data to visualization queue
        data_queue.put({
            'timestamp': timestamp,
            'left': left_distance,
            'right': right_distance
        })
        
        # Save to CSV
        save_to_csv(timestamp, left_distance, right_distance)
        
        # Log the received data
        logging.info(f"Received - Left: {left_distance}cm, Right: {right_distance}cm")
        time.sleep(1)
        return "Data received successfully", 200
    
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return f"Error: {str(e)}", 400

@app.route('/toggle_audio', methods=['POST'])
def toggle_audio():
    global audio_enabled
    audio_enabled = not audio_enabled
    
    if audio_enabled:
        tone_gen.start()
        return "Audio enabled", 200
    else:
        tone_gen.stop()
        return "Audio disabled", 200

@app.route('/clear_plot', methods=['POST'])
def clear_plot():
    distances_left.clear()
    distances_right.clear()
    timestamps.clear()
    plt.clf()
    return "Plot cleared", 200

last_button_status = "not pressed"  # Initialize the last status

def check_button_status():
    global last_button_status
    while True:
        try:
            response = requests.get(f"http://{ESP32_IP}/getButtonStatus")
            if response.status_code == 200:
                button_status = response.text.strip()
                # Only capture if the button status has just changed to "pressed"
                if button_status == "pressed" and last_button_status == "not pressed":
                    print('Button Pressed')
                    capture_and_process_image()
                # Update the last known status
                last_button_status = button_status
        except requests.exceptions.RequestException:
            print("Error connecting to ESP32")
        time.sleep(0.5)  # Delay to prevent excessive requests


if __name__ == '__main__':
    # Start visualization thread
    #viz_thread = threading.Thread(target=visualization_thread, daemon=True)
    #viz_thread.start()
    button_thread = threading.Thread(target=check_button_status, daemon=True)
    button_thread.start()
    # Start sensor polling thread
    sensor_thread = threading.Thread(target=poll_sensor_data, daemon=True)
    sensor_thread.start()

    PORT = 4443
    print("\nServer IP Addresses:")
    print("-" * 50)
    
    # Get and display all IP addresses
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                if not ip.startswith('127.'):
                    print(f"Interface: {interface:<15} IP: {ip:<15}")
                    print(f"Access the server at: http://{ip}:{PORT}")
    
    print("-" * 50)
    print("\nServer is running! Press CTRL+C to stop.")
    print("\nAvailable endpoints:")
    print(f"POST /          - Send sensor data")
    print(f"POST /toggle_audio - Toggle audio feedback")
    print(f"POST /clear_plot  - Clear visualization")
    print(f"POST /ocr_button  - Process image and display OCR results")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=False  # Set to False when using threads
    )
