from PIL import Image
import io
import cv2
from pathlib import Path
import numpy as np

def compress_image(file_bytes: bytes, quality: int = 60) -> bytes:
    """
    Compress the image using Pillow to lower JPEG quality while keeping resolution.
    
    Args:
        file_bytes (bytes): Original image bytes.
        quality (int): JPEG quality level (lower means more compression).
        
    Returns:
        bytes: Compressed image bytes.
    """
    input_buffer = io.BytesIO(file_bytes)
    try:
        # Open the image using Pillow
        image = Image.open(input_buffer)
    except Exception as e:
        raise ValueError(f"Error opening image: {e}")

    output_buffer = io.BytesIO()
    # Save the image with the desired JPEG quality
    image.save(output_buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
    return output_buffer.getvalue()

def decode_image(file_bytes):
    """Convert file bytes into a cv2 image (BGR)"""
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def encode_image(cv_image):
    """Convert cv2 image into file bytes (BGR)"""
    is_success, file_bytes = cv2.imencode(".jpg", cv_image)
    return is_success, file_bytes

def store_image(output_dir:str, file_name_prefix:str, cv_image:np.ndarray, quality:int=65):
    """
    Save the augmented image.

    Args:
        output_dir (str): Output directory.
        file_name_prefix (str): File name prefix.
        image (numpy.ndarray): Image to save.
        mask (numpy.ndarray, optional): Mask to save.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / f"{file_name_prefix}"
    image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(image_rgb)

    pil_img.save(
        str(image_path),
        format="JPEG",
        quality=quality,
        optimize=True
    )

    return str(image_path)