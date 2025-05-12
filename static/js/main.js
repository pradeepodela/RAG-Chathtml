// Main JavaScript for Document Q&A System

document.addEventListener('DOMContentLoaded', function() {
    // Handle flash message close buttons
    const closeButtons = document.querySelectorAll('.close-flash');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const flashMessage = this.closest('.flash-message');
            flashMessage.style.opacity = '0';
            flashMessage.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                flashMessage.remove();
            }, 300);
        });
    });
    
    // Auto-hide flash messages after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.flash-message').forEach(message => {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                message.remove();
            }, 300);
        });
    }, 5000);
    
    // Upload form progress handling
    const uploadForm = document.getElementById('upload-form');
    const uploadButton = document.getElementById('upload-button');
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            // Show loading state
            uploadButton.disabled = true;
            uploadButton.innerHTML = '<div class="flex items-center"><div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div> Processing...</div>';
        });
    }
    
    // Responsive sidebar toggle for mobile
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('hidden');
            sidebar.classList.toggle('md:block');
        });
    }
    
    // Support for markdown rendering in chat messages
    const markdownElements = document.querySelectorAll('.markdown-content');
    if (markdownElements.length > 0 && typeof marked !== 'undefined') {
        markdownElements.forEach(element => {
            const content = element.innerHTML;
            element.innerHTML = marked.parse(content);
        });
    }

    // Chat input focus
    const chatInput = document.getElementById('chat-input');
    if (chatInput && !chatInput.disabled) {
        chatInput.focus();
    }

    // Handle enter key in chat input
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                
                const chatForm = document.getElementById('chat-form');
                if (chatForm) {
                    const submitEvent = new Event('submit', {
                        'bubbles': true,
                        'cancelable': true
                    });
                    chatForm.dispatchEvent(submitEvent);
                }
            }
        });
    }
});