import base64

import requests
from PIL import Image
from together import Together

client = Together(api_key="f79744841a9d211621a12f924b810dab2a71a48375b78a094372fb9ae3c9fbe6")

ESP32_IP = "192.168.144.225"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_description(image_path):
    getDescriptionPrompt = "what is in the image"
    base64_image = encode_image(image_path)
    
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        messages=[
            {
                "role": "user",
                "content": getDescriptionPrompt + "\n" + f"data:image/jpeg;base64,{base64_image}"
            }
        ],
        stream=True
    )

    description = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            description += chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content, end="", flush=True)
    return description


if __name__ == "__main__":
    
    capture_url = f"http://{ESP32_IP}/capture"
    response = requests.get(capture_url)

    # Save captured image temporarily
    temp_image_path = "temp_capture.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(response.content)

    Image.open(temp_image_path).show()
    get_image_description("./temp_capture.jpg")