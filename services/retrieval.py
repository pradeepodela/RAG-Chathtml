from haystack import Pipeline
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever, InMemoryEmbeddingRetriever
from haystack.components.joiners import DocumentJoiner
from haystack.components.rankers import TransformersSimilarityRanker
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.ollama import OllamaGenerator

from .document_store import document_store_service
from config import get_config

class RetrievalService:
    """Service for handling document retrieval and query operations"""
    
    def __init__(self):
        """Initialize the retrieval service"""
        config = get_config()
        self.document_store = document_store_service.get_document_store()
        self.embedding_model = config.EMBEDDING_MODEL
        self.reranker_model = config.RERANKER_MODEL
        self.ollama_url = config.OLLAMA_URL
        self.ollama_model = config.OLLAMA_MODEL
        self.top_k = config.TOP_K_RETRIEVER
        
        self._initialize_pipelines()
    
    def _initialize_pipelines(self):
        """Initialize retrieval and citation pipelines"""
        # Initialize the retrieval pipeline
        self._initialize_retrieval_pipeline()
        
        # Initialize the citation pipeline
        self._initialize_citation_pipeline()
    
    def _initialize_retrieval_pipeline(self):
        """Initialize the main retrieval and generation pipeline"""
        # Text embedder and retrievers
        text_embedder = SentenceTransformersTextEmbedder(model=self.embedding_model)
        embedding_retriever = InMemoryEmbeddingRetriever(self.document_store)
        bm25_retriever = InMemoryBM25Retriever(self.document_store)
        document_joiner = DocumentJoiner()
        ranker = TransformersSimilarityRanker(model=self.reranker_model)
        
        # Set up prompt template with citation formatting
        template = """
        Act as a senior customer care executive and help users with their queries. Be polite and friendly. Answer the user's questions based on the below context:
        
        CONTEXT:
        {% for document in documents %}
            {{ document.content }} [Source: {{ document.meta.file_name }}, Page: {{ document.meta.page_number }}]
        {% endfor %}
        
        Make sure to provide all the details. If the answer is not in the provided context just say, 'Answer is not available in the context'. Don't provide wrong information.
        If the user asks for any external recommendation only provide information related to the documents you received.
        If user asks you anything other than what's in the context, just say 'Sorry, I can't help you with that'.

        Question: {{question}}

        Please explain in detail with a crystal clear format.
        """
        
        prompt_builder = PromptBuilder(template=template)
        
        # Set up Ollama Generator
        generator = OllamaGenerator(model=self.ollama_model, url=self.ollama_url)
        
        # Create retrieval pipeline
        self.retrieval_pipeline = Pipeline()
        self.retrieval_pipeline.add_component("text_embedder", text_embedder)
        self.retrieval_pipeline.add_component("embedding_retriever", embedding_retriever)
        self.retrieval_pipeline.add_component("bm25_retriever", bm25_retriever)
        self.retrieval_pipeline.add_component("document_joiner", document_joiner)
        self.retrieval_pipeline.add_component("ranker", ranker)
        self.retrieval_pipeline.add_component("prompt_builder", prompt_builder)
        self.retrieval_pipeline.add_component("llm", generator)
        
        # Connect pipeline components
        self.retrieval_pipeline.connect("text_embedder", "embedding_retriever")
        self.retrieval_pipeline.connect("bm25_retriever", "document_joiner")
        self.retrieval_pipeline.connect("embedding_retriever", "document_joiner")
        self.retrieval_pipeline.connect("document_joiner", "ranker")
        self.retrieval_pipeline.connect("ranker", "prompt_builder.documents")
        self.retrieval_pipeline.connect("prompt_builder", "llm")
    
    def _initialize_citation_pipeline(self):
        """Initialize the pipeline for citations"""
        # Components for citation
        text_embedder = SentenceTransformersTextEmbedder(model=self.embedding_model)
        embedding_retriever = InMemoryEmbeddingRetriever(self.document_store)
        bm25_retriever = InMemoryBM25Retriever(self.document_store)
        document_joiner = DocumentJoiner()
        ranker = TransformersSimilarityRanker(model=self.reranker_model)

        # Create citation pipeline
        self.citation_pipeline = Pipeline()
        self.citation_pipeline.add_component("text_embedder", text_embedder)
        self.citation_pipeline.add_component("embedding_retriever", embedding_retriever)
        self.citation_pipeline.add_component("bm25_retriever", bm25_retriever)
        self.citation_pipeline.add_component("document_joiner", document_joiner)
        self.citation_pipeline.add_component("ranker", ranker)

        # Connect citation pipeline components
        self.citation_pipeline.connect("text_embedder", "embedding_retriever")
        self.citation_pipeline.connect("bm25_retriever", "document_joiner")
        self.citation_pipeline.connect("embedding_retriever", "document_joiner")
        self.citation_pipeline.connect("document_joiner", "ranker")
    
    def query(self, query_text, citation_format="brief"):
        """
        Process a query and generate a response
        
        Args:
            query_text: The user's query
            citation_format: Format for citations ('brief' or 'detailed')
            
        Returns:
            dict: Response with answer and citations
        """
        try:
            # Run the retrieval pipeline
            result = self.retrieval_pipeline.run(
                {
                    "text_embedder": {"text": query_text},
                    "bm25_retriever": {"query": query_text},
                    "ranker": {"query": query_text},
                    "prompt_builder": {"question": query_text}
                }
            )
            
            # Get citation information
            citation_result = self.citation_pipeline.run(
                {
                    "text_embedder": {"text": query_text},
                    "bm25_retriever": {"query": query_text},
                    "ranker": {"query": query_text}
                }
            )
            
            # Extract the response
            response = result['llm']['replies'][0]
            
            # Format citations
            citations = []
            seen_citations = set()  # To avoid duplicates
            
            for doc in citation_result['ranker']['documents'][:self.top_k]:
                file_name = doc.meta.get('file_name', 'Unknown')
                page_number = doc.meta.get('page_number', 'Unknown')
                score = round(doc.score * 100, 1) if hasattr(doc, 'score') else None
                
                citation_key = f"{file_name}:{page_number}"
                if citation_key not in seen_citations:
                    if citation_format == "brief":
                        citations.append({
                            "file_name": file_name,
                            "page": page_number,
                            "score": score,
                            "text": f"[{file_name}, Page {page_number}]"
                        })
                    else:
                        citations.append({
                            "file_name": file_name,
                            "page": page_number,
                            "score": score,
                            "text": f"[{file_name}, Page {page_number}, Relevance: {score}%]"
                        })
                    seen_citations.add(citation_key)
            
            return {
                "answer": response,
                "citations": citations
            }
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return {
                "answer": f"Error generating response: {str(e)}",
                "citations": []
            }