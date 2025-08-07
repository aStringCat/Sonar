# image_downloader.py
# This script downloads an image from a URL.

import requests
import os

def download_image(url, save_as):
    """Downloads an image from a specific URL and saves it to a file."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        with open(save_as, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Image successfully downloaded and saved as '{save_as}'")
        return True
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during download: {e}")
        return False

# URL of a sample image (e.g., a public domain image)
image_url = "https://www.nasa.gov/wp-content/uploads/2023/04/j2m-shareable.jpg"
filename = "nasa_image.jpg"

if not os.path.exists(filename):
    download_image(image_url, filename)
else:
    print(f"File '{filename}' already exists. Skipping download.")