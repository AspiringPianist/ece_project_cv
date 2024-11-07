import argparse
import time
from pathlib import Path
#from gpiozero import Button
import requests
import base64

def run_ocr(image_path):
    api_key = 'K84458401488957'
    
    try:
        # Load and convert image to base64
        with open(image_path, 'rb') as image_file:
            img_byte_arr = image_file.read()
        base64_img = base64.b64encode(img_byte_arr).decode()
        
        payload = {
            'base64Image': f'data:image/jpeg;base64,{base64_img}',
            'language': 'eng',
            'isOverlayRequired': False,
            'OCREngine': 2,
            'scale': True,
            'detectOrientation': True
        }
        
        url = 'https://api.ocr.space/parse/image'
        headers = {
            'apikey': api_key,
        }
        
        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        
        if result.get('ParsedResults'):
            text = result['ParsedResults'][0]['ParsedText'].strip()
            if text:
                return text
            return "No text detected or unclear text."
        return "No text detected or unclear text."
            
    except Exception as e:
        print(f'Error processing image: {str(e)}')