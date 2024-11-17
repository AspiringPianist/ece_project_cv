import os
import google.generativeai as genai
import pyttsx3

# Configure the Gemini API key from environment variables
genai.configure(api_key="AIzaSyB-Lghd5AdWpBeApKSFPZbqXh-TuYF3OQg")

def upload_to_gemini(path, mime_type="image/jpeg"):
    """Uploads the given file to Gemini, handling any errors."""
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        return f"Error uploading file: {e}"

def run_ocr(image_path_on_computer):
    """Uploads the given image, sends a request for OCR, and returns the response text."""
    # Initialize text-to-speech engine
    #engine = pyttsx3.init()
    
    # Upload the image file to Gemini
    file = upload_to_gemini(image_path_on_computer)
    if isinstance(file, str):  # check if an error message was returned
        #engine.say(file)
        #engine.runAndWait()
        return file

    # Define model configuration for generation
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    # Create a new model instance with the specified configuration
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-002",
        generation_config=generation_config,
    )

    # Start a new chat session without previous context
    try:
        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [
                        file,
                        "this is the image which is what i am seeing in front of my eyes",
                    ],
                },
            ]
        )

        # Send message to retrieve response from model
        response = chat_session.send_message("describe the scene concisely and effectively in such a way that it is helpful for a blind person, make it more context and less descriptive about objects (1-2 lines)")
        # Speak the response
        print(response.text)
        #engine.say(response.text)
        #engine.runAndWait()
        return response.text

    except Exception as e:
        error_message = f"Error during OCR processing: {e}"
        #engine.say(error_message)
        #engine.runAndWait()
        return error_message
