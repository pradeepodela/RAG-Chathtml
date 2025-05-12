from haystack.document_stores.in_memory import InMemoryDocumentStore

class DocumentStoreService:
    """Service for handling document storage operations"""
    
    def __init__(self):
        """Initialize the document store"""
        self.document_store = InMemoryDocumentStore()
        self.processed_files = []
    
    def get_document_store(self):
        """Get the document store instance"""
        return self.document_store
    
    def add_processed_file(self, filename):
        """Add a filename to the list of processed files"""
        if filename not in self.processed_files:
            self.processed_files.append(filename)
    
    def get_processed_files(self):
        """Get the list of processed files"""
        return self.processed_files
    
    def is_file_processed(self, filename):
        """Check if a file has been processed"""
        return filename in self.processed_files
    
    def get_document_count(self):
        """Get the number of documents in the store"""
        return self.document_store.count_documents()
    
    def clear(self):
        """Clear the document store and processed files list"""
        self.document_store = InMemoryDocumentStore()
        self.processed_files = []
        return True

# Singleton instance
document_store_service = DocumentStoreService()