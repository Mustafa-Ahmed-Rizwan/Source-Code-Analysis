document.addEventListener('DOMContentLoaded', () => {
    const repoUrlInput = document.getElementById('repo-url');
    const ingestBtn = document.getElementById('ingest-btn');
    const repoMessage = document.getElementById('repo-message');
    const chatSection = document.getElementById('chat-section');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const chatMessages = document.getElementById('chat-messages');
    const chatMessage = document.getElementById('chat-message');
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const newChatBtn = document.getElementById('new-chat-btn');

    let isInitialized = false;

    // Set default: light mode
    document.body.classList.remove('dark-mode');
    if (darkModeToggle) darkModeToggle.checked = false;

    // Load dark mode preference from localStorage
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        if (darkModeToggle) darkModeToggle.checked = true;
    }

    // Toggle dark mode on checkbox change
    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', () => {
            if (darkModeToggle.checked) {
                document.body.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'true');
            } else {
                document.body.classList.remove('dark-mode');
                localStorage.setItem('darkMode', 'false');
            }
        });
    }

    // Handle repository ingestion
    ingestBtn.addEventListener('click', async () => {
        const repoUrl = repoUrlInput.value.trim();
        if (!repoUrl) {
            repoMessage.textContent = 'Please enter a valid GitHub repository URL.';
            repoMessage.classList.add('text-red-500');
            return;
        }
        ingestBtn.disabled = true;
        ingestBtn.textContent = 'Ingesting...';
        repoMessage.textContent = 'Processing repository...';
        repoMessage.classList.remove('text-red-500', 'text-green-500');

        try {
            // When initializing
            repoMessage.textContent = 'Initializing embeddings and processing repository... This may take a moment.';
            repoMessage.classList.remove('text-green-400', 'text-red-400');
            repoMessage.classList.add('text-gray-500');

            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `question=${encodeURIComponent(repoUrl)}`
            });
            const data = await response.json();

            // When you get a response:
            repoMessage.textContent = data.response;
            repoMessage.classList.remove('text-green-400', 'text-red-400', 'text-gray-500');
            if (
                data.response.toLowerCase().includes('success') ||
                data.response.toLowerCase().includes('repository already exists')
            ) {
                repoMessage.classList.add('text-green-400');
                chatSection.classList.remove('hidden');
                isInitialized = true;
            } else {
                repoMessage.classList.add('text-red-400');
            }
        } catch (error) {
            repoMessage.textContent = 'Error: Failed to process repository.';
            repoMessage.classList.remove('text-green-400', 'text-gray-500');
            repoMessage.classList.add('text-red-400');
        } finally {
            ingestBtn.disabled = false;
            ingestBtn.textContent = 'Ingest';
        }
    });

    // Handle chat message
    sendBtn.addEventListener('click', async () => {
        const message = chatInput.value.trim();
        if (!message) {
            chatMessage.textContent = 'Please enter a question.';
            chatMessage.classList.add('text-red-500');
            return;
        }
        if (!isInitialized) {
            chatMessage.textContent = 'Please ingest a repository first.';
            chatMessage.classList.add('text-red-500');
            return;
        }

        const userDiv = document.createElement('div');
        userDiv.className = 'message user-message';
        userDiv.textContent = message;
        chatMessages.appendChild(userDiv);
        window.scrollTo(0, document.body.scrollHeight);

        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';
        chatMessage.textContent = '';
        chatInput.value = '';

        try {
            const response = await fetch('/get', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `msg=${encodeURIComponent(message)}`
            });
            const data = await response.json();

            const botDiv = document.createElement('div');
            botDiv.className = 'message bot-message';
            try {
                const markdown = marked.parse(data.response, { gfm: true, breaks: true });
                botDiv.innerHTML = markdown;
                botDiv.querySelectorAll('pre').forEach(pre => {
                    pre.classList.add('code-snippet');
                    const code = pre.querySelector('code');
                    if (code) code.style.backgroundColor = 'transparent';
                });
                // Verify and apply width if not set
                if (botDiv.style.width === '') {
                    botDiv.style.width = '600px'; // Ensure the width is applied
                }
            } catch (e) {
                const para = document.createElement('p');
                para.className = 'paragraph';
                para.textContent = data.response;
                botDiv.appendChild(para);
            }
            chatMessages.appendChild(botDiv);
            window.scrollTo(0, document.body.scrollHeight);
        } catch (error) {
            chatMessage.textContent = 'Error: Failed to get response.';
            chatMessage.classList.add('text-red-500');
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send';
        }
    });

    // Handle clear chat button
    clearChatBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/get', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'msg=clear_chat'
            });
            const data = await response.json();
            chatMessage.textContent = data.response || ''; // Only set if response exists
            if (data.response) chatMessage.classList.add('text-green-500');
            chatMessages.innerHTML = '';
        } catch (error) {
            chatMessage.textContent = 'Error: Failed to clear chat history.';
            chatMessage.classList.add('text-red-500');
        }
    });

    // Handle new chat button to clear repo and chat
    newChatBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/get', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'msg=clear_repo'
            });
            const data = await response.json();
            if (data.type === 'repo') {
                chatMessage.textContent = '';
                chatMessages.innerHTML = '';
                isInitialized = false;
                // Hide chat section and reset repo input/message
                chatSection.classList.add('hidden');
                repoMessage.textContent = '';
                repoUrlInput.value = '';
                // Also remove any status classes
                repoMessage.classList.remove('text-green-500', 'text-red-500');
            } else if (data.response) {
                chatMessage.textContent = data.response;
                chatMessage.classList.add('text-green-500');
                chatMessages.innerHTML = '';
                isInitialized = false;
                chatSection.classList.add('hidden');
                repoMessage.textContent = '';
                repoUrlInput.value = '';
                repoMessage.classList.remove('text-green-500', 'text-red-500');
            }
        } catch (error) {
            chatMessage.textContent = 'Error: Failed to clear repository and index.';
            chatMessage.classList.add('text-red-500');
        }
    });

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendBtn.click();
        }
    });

    repoUrlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            ingestBtn.click();
        }
    });
});