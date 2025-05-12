import os
import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, jsonify, session
)
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from config import get_config
from services.document_store import document_store_service
from services.indexing import IndexingService
from services.retrieval import RetrievalService
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

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(get_config())

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for services
indexing_service = None
retrieval_service = None

def initialize_services():
    """Initialize the indexing and retrieval services"""
    global indexing_service, retrieval_service
    
    if not indexing_service:
        indexing_service = IndexingService(app.config['EMBEDDING_MODEL'])
    
    if not retrieval_service:
        retrieval_service = RetrievalService()

# Context processor for templates
@app.context_processor
def inject_globals():
    """Inject global variables into templates"""
    return {
        'current_year': datetime.datetime.now().year,
        'document_count': len(document_store_service.get_processed_files()),
        'chunk_count': document_store_service.get_document_count()
    }

@app.route('/')
def index():
    """Render the main page"""
    initialize_services()
    
    # Initialize messages in session if not present
    if 'messages' not in session:
        session['messages'] = []
    
    messages = session.get('messages', [])
    processed_files = document_store_service.get_processed_files()
    
    return render_template(
        'index.html',
        messages=messages,
        processed_files=processed_files
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    # Check if there are any files
    if 'files[]' not in request.files:
        flash('No files selected', 'warning')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files[]')
    
    # Check if files are empty
    if not files or files[0].filename == '':
        flash('No files selected', 'warning')
        return redirect(url_for('index'))
    
    # Initialize services if needed
    initialize_services()
    
    # Temporary file storage
    temp_files = []
    processed_count = 0
    
    try:
        for file in files:
            if file and allowed_file(file.filename):
                # Save file to disk
                file_info = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
                temp_files.append(file_info['path'])
                
                # Process file
                if indexing_service.process_document(file_info['path'], file_info['original_name']):
                    processed_count += 1
    
        if processed_count > 0:
            flash(f'Successfully processed {processed_count} document(s)', 'success')
        else:
            flash('No documents were processed', 'warning')
    
    except Exception as e:
        flash(f'Error processing documents: {str(e)}', 'error')
    
    finally:
        # Clean up temporary files
        clean_temp_files(temp_files)
    
    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    """Reset the application state"""
    # Clear document store
    document_store_service.clear()
    
    # Clear session messages
    session['messages'] = []
    session.modified = True
    
    # Reset services
    global indexing_service, retrieval_service
    indexing_service = None
    retrieval_service = None
    
    flash('All data has been reset', 'success')
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming messages via SocketIO"""
    # Extract message and citation format
    message = data.get('message', '')
    citation_format = data.get('citation_format', 'brief')
    
    if not message:
        return
    
    # Add message to session
    timestamp = datetime.datetime.now()
    user_message = {
        'role': 'user',
        'content': message,
        'timestamp': timestamp
    }
    
    session['messages'] = session.get('messages', []) + [user_message]
    session.modified = True
    
    # Initialize services if needed
    initialize_services()
    
    try:
        # Process the query
        result = retrieval_service.query(message, citation_format)
        
        # Create assistant message
        assistant_message = {
            'role': 'assistant',
            'content': result['answer'],
            'citations': result['citations'],
            'timestamp': datetime.datetime.now()
        }
        
        # Add to session
        session['messages'] = session.get('messages', []) + [assistant_message]
        session.modified = True
        
        # Emit response back to client
        emit('receive_message', {
            'answer': result['answer'],
            'citations': result['citations']
        })
        
    except Exception as e:
        error_message = f"Error generating response: {str(e)}"
        
        # Add error message to session
        error_assistant_message = {
            'role': 'assistant',
            'content': error_message,
            'citations': [],
            'timestamp': datetime.datetime.now()
        }
        
        session['messages'] = session.get('messages', []) + [error_assistant_message]
        session.modified = True
        
        # Emit error response
        emit('receive_message', {
            'answer': error_message,
            'citations': []
        })

if __name__ == '__main__':
    socketio.run(app, debug=app.config['DEBUG'])