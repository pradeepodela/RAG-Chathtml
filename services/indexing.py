from haystack import Pipeline
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.components.converters import PyPDFToDocument

from .document_store import document_store_service

class IndexingService:
    """Service for handling document indexing operations"""
    
    def __init__(self, embedding_model):
        """
        Initialize the indexing service
        
        Args:
            embedding_model: Model name for document embedding
        """
        self.embedding_model = embedding_model
        self.document_store = document_store_service.get_document_store()
        self._initialize_pipeline()
    
    def _initialize_pipeline(self):
        """Initialize the indexing pipeline"""
        document_embedder = SentenceTransformersDocumentEmbedder(
            model=self.embedding_model
        )
        
        # Create indexing pipeline
        self.pipeline = Pipeline()
        self.pipeline.add_component("converter", PyPDFToDocument())
        self.pipeline.add_component("splitter", DocumentSplitter(split_by="sentence", split_length=2))
        self.pipeline.add_component("embedder", document_embedder)
        self.pipeline.add_component("writer", DocumentWriter(self.document_store))
        
        # Connect indexing pipeline components
        self.pipeline.connect("converter", "splitter")
        self.pipeline.connect("splitter", "embedder")
        self.pipeline.connect("embedder", "writer")
    
    def process_document(self, file_path, file_name):
        """
        Process a document and add it to the document store
        
        Args:
            file_path: Path to the file
            file_name: Original name of the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Run indexing pipeline
            self.pipeline.run({
                "converter": {
                    "sources": [file_path], 
                    "meta": {"file_name": file_name}
                }
            })
            
            # Add to processed files
            document_store_service.add_processed_file(file_name)
            
            return True
        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            return False