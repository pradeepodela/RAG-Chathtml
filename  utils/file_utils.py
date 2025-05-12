import os
import uuid
from werkzeug.utils import secure_filename

def allowed_file(filename, allowed_extensions=None):
    """Check if the file has an allowed extension"""
    if allowed_extensions is None:
        allowed_extensions = {'pdf'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_folder):
    """
    Save uploaded file to disk with a secure filename
    
    Args:
        file: The file object from request.files
        upload_folder: Directory to save the file
        
    Returns:
        dict: Information about the saved file (path, name, etc.)
    """
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Secure the filename and make it unique
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(upload_folder, unique_filename)
    
    # Save the file
    file.save(file_path)
    
    return {
        'original_name': filename,
        'saved_name': unique_filename,
        'path': file_path
    }

def get_file_info(file_path):
    """
    Extract information about a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        dict: File information
    """
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    return {
        'filename': filename,
        'size': file_size,
        'path': file_path
    }

def clean_temp_files(file_paths):
    """
    Remove temporary files after processing
    
    Args:
        file_paths: List of file paths to remove
    """
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Error removing file {path}: {str(e)}")