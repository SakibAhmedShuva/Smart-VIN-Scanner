from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
from pyzbar.pyzbar import decode
from PIL import Image
import io
import os
import uuid

app = Flask(__name__)
CORS(app)

# Directory for storing barcode images
UPLOAD_FOLDER = 'uploads/barcodes'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Define a margin in pixels
MARGIN = 5

def convert_to_jpg(image):
    """Convert image to RGB mode and return as JPEG."""
    # Convert RGBA to RGB if necessary
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    return image

def save_image_locally(image, filename):
    """Save image to local directory and return the file path."""
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image.save(filepath, 'JPEG', quality=100)
        return filepath
    except Exception as e:
        print(f"Error saving file locally: {str(e)}")
        raise

@app.route('/uploads/barcodes/<filename>')
def serve_file(filename):
    """Serve the uploaded files."""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/vindata', methods=['POST'])
def get_vin_data():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    image_file = request.files['image']
    
    try:
        # Read the image file
        image = Image.open(io.BytesIO(image_file.read()))
        
        # Convert to JPG format
        image = convert_to_jpg(image)
        
    except IOError:
        return jsonify({'error': 'Invalid image file'}), 400

    barcodes = decode(image)

    if not barcodes:
        return jsonify({'message': 'No barcodes found'}), 200

    results = []
    for barcode in barcodes:
        decoded_data = barcode.data.decode('utf-8')
        
        # Crop the barcode with margin
        x, y, w, h = barcode.rect
        x = max(x - MARGIN, 0)
        y = max(y - MARGIN, 0)
        w = w + 2 * MARGIN
        h = h + 2 * MARGIN
        barcode_image = image.crop((x, y, x + w, y + h))

        # Generate unique filename
        barcode_filename = f"{uuid.uuid4().hex}.jpg"
        
        try:
            # Save locally
            filepath = save_image_locally(barcode_image, barcode_filename)
            # Generate URL for the saved image
            barcode_link = f"/uploads/barcodes/{barcode_filename}"
        except Exception as e:
            return jsonify({'error': f'Failed to save image: {str(e)}'}), 500
        
        results.append({
            'barcode_data': decoded_data,
            'barcode_link': barcode_link
        })

    return jsonify({'result': results}), 200

if __name__ == '__main__':
    app.run(debug=True)