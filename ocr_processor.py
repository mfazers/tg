import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import os
from config import TESSERACT_PATH

# Set Tesseract path if configured
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def preprocess_image(image_path):
    """
    Preprocess image to improve OCR accuracy
    """
    # Read image
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply threshold to get binary image
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Morphological operations to clean up the image
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    return opening

def extract_hours_from_image(image_path):
    """
    Extract hours worked from a time sheet image
    Returns a list of possible hour values found in the image
    """
    try:
        # Preprocess the image
        processed_img = preprocess_image(image_path)
        
        # Use Tesseract to extract text
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789. '
        text = pytesseract.image_to_string(processed_img, config=custom_config)
        
        # Find numbers that look like hours (including decimals)
        # Pattern looks for numbers like: 8, 8.5, 40, etc.
        hour_pattern = r'\b\d{1,2}(?:\.\d)?\b'
        matches = re.findall(hour_pattern, text)
        
        # Convert to float and filter out unlikely values
        hours_list = []
        for match in matches:
            try:
                hour_val = float(match)
                # Reasonable range for work hours (0.1 to 24 hours per day)
                if 0.1 <= hour_val <= 24:
                    hours_list.append(hour_val)
            except ValueError:
                continue
        
        # Return the most likely hour value (highest in reasonable range)
        if hours_list:
            return max(hours_list), hours_list
        else:
            # If no hours found in reasonable range, try broader search
            broader_pattern = r'\d+(?:\.\d+)?'
            broader_matches = re.findall(broader_pattern, text)
            for match in broader_matches:
                try:
                    hour_val = float(match)
                    if 0.1 <= hour_val <= 100:  # More generous upper limit
                        hours_list.append(hour_val)
                except ValueError:
                    continue
            
            if hours_list:
                return max(hours_list), hours_list
    
    except Exception as e:
        print(f"Error in OCR processing: {str(e)}")
        return None, []
    
    return None, []

def validate_hour_value(hour_value):
    """
    Validate if the extracted hour value is reasonable
    """
    if hour_value is None:
        return False
    
    # Check if it's within reasonable work hours
    if 0.1 <= hour_value <= 24:
        return True
    
    # For weekly totals, might be higher
    if 24 < hour_value <= 80:
        return True
    
    return False

def process_timesheet_image(image_path):
    """
    Process a timesheet image and extract hours worked
    """
    hour_value, all_matches = extract_hours_from_image(image_path)
    
    if validate_hour_value(hour_value):
        return {
            'success': True,
            'hours': hour_value,
            'all_matches': all_matches,
            'confidence': calculate_confidence(hour_value, all_matches)
        }
    else:
        return {
            'success': False,
            'hours': None,
            'all_matches': all_matches,
            'error': 'No valid hour value found in image',
            'confidence': 0
        }

def calculate_confidence(hour_value, all_matches):
    """
    Calculate confidence level for the extracted hour value
    """
    if not all_matches:
        return 0
    
    # Confidence based on how many similar values were found
    similar_values = [h for h in all_matches if abs(h - hour_value) < 1.0]
    confidence = len(similar_values) / len(all_matches)
    
    # Additional factors could be added here
    return min(confidence, 1.0)  # Cap at 1.0

# Test function
def test_ocr():
    """
    Test the OCR functionality with a sample image
    """
    # This would be used to test with a real image file
    pass