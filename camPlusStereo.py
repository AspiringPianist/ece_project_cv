from flask import Flask, request
import logging
from datetime import datetime
import json
import socket
import netifaces
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from collections import deque
import csv
import threading
from queue import Queue
import time
from scipy import signal
import requests
import pyttsx3
from PIL import Image
from io import BytesIO
from ocr import run_ocr
import os

ESP32_IP = "192.168.144.225"
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
        
# Initialize Flask app
app = Flask(__name__)

# Audio parameters
SAMPLE_RATE = 44100
BLOCK_SIZE = 2048
FREQ_LEFT = 440   # A4 note for left channel
FREQ_RIGHT = 880  # A5 note for right channel

# Distance to volume mapping parameters
MAX_DISTANCE = 200  # cm
MIN_DISTANCE = 10   # cm

# Data visualization setup
MAX_POINTS = 100
distances_left = deque(maxlen=MAX_POINTS)
distances_right = deque(maxlen=MAX_POINTS)
timestamps = deque(maxlen=MAX_POINTS)

# Global flags and data queue
audio_enabled = True
data_queue = Queue()

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
        outdata[:, 0] = left_filtered * self.volume_left
        outdata[:, 1] = right_filtered * self.volume_right# Initialize audio generator
tone_gen = StereoToneGenerator()

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

def update_plot():
    plt.clf()
    plt.plot(list(timestamps), list(distances_left), label='Left Sensor', color='blue')
    plt.plot(list(timestamps), list(distances_right), label='Right Sensor', color='red')
    plt.xlabel('Time')
    plt.ylabel('Distance (cm)')
    plt.title('Stereo Ultrasonic Sensor Data')
    plt.legend()
    plt.grid(True)
    plt.pause(0.01)

def visualization_thread():
    plt.ion()  # Enable interactive mode
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            distances_left.append(int(data['left']))
            distances_right.append(int(data['right']))
            timestamps.append(data['timestamp'])
            update_plot()
        time.sleep(0.1)

@app.route('/', methods=['POST'])
def receive_data():
    try:
        # Get distance values from POST request
        left_distance = float(request.form.get('left', 0))
        right_distance = float(request.form.get('right', 0))
        
        # Create timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Update audio if enabled
        if audio_enabled:
            tone_gen.update_volumes(left_distance, right_distance)
        
        # Add data to visualization queue
        data_queue.put({
            'timestamp': timestamp,
            'left': float(left_distance),
            'right': float(right_distance)
        })
        
        # Save to CSV
        save_to_csv(timestamp, left_distance, right_distance)
        
        # Log the received data
        logging.info(f"Received - Left: {left_distance}cm, Right: {right_distance}cm")
        
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

@app.route('/ocr_button', methods=['POST'])
def ocr_button():
    # Capture image and process
    capture_and_process_image()
    return "Image processed", 200

if __name__ == '__main__':
    # Start visualization thread
    viz_thread = threading.Thread(target=visualization_thread, daemon=True)
    viz_thread.start()
    
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
