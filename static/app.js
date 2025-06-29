document.addEventListener('DOMContentLoaded', () => {
    const repoUrlInput = document.getElementById('repo-url');
    const ingestBtn = document.getElementById('ingest-btn');
    const repoMessage = document.getElementById('repo-message');
    const chatSection = document.getElementById('chat-section');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const clearBtn = document.getElementById('clear-btn');
    const chatContainer = document.getElementById('chat-container');
    const chatMessage = document.getElementById('chat-message');

    let isInitialized = false;

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
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `question=${encodeURIComponent(repoUrl)}`
            });
            const data = await response.json();
            repoMessage.textContent = data.response;
            if (data.response.includes('success') || data.response.includes('Repository already exists')) {
                repoMessage.classList.add('text-green-500');
                chatSection.classList.remove('hidden');
                isInitialized = true;
            } else {
                repoMessage.classList.add('text-red-500');
            }
        } catch (error) {
            repoMessage.textContent = 'Error: Failed to ingest repository.';
            repoMessage.classList.add('text-red-500');
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

        // Add user message to chat
        const userDiv = document.createElement('div');
        userDiv.className = 'message user-message';
        userDiv.textContent = message;
        chatContainer.appendChild(userDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

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
            botDiv.textContent = data.response;
            chatContainer.appendChild(botDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        } catch (error) {
            chatMessage.textContent = 'Error: Failed to get response.';
            chatMessage.classList.add('text-red-500');
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send';
        }
    });

    // Handle clear button
    clearBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/get', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'msg=clear'
            });
            const data = await response.json();
            chatMessage.textContent = data.response;
            chatMessage.classList.add('text-green-500');
            chatContainer.innerHTML = '';
            chatSection.classList.add('hidden');
            isInitialized = false;
            repoUrlInput.value = '';
            repoMessage.textContent = '';
        } catch (error) {
            chatMessage.textContent = 'Error: Failed to clear repository.';
            chatMessage.classList.add('text-red-500');
        }
    });

    // Allow sending message with Enter key
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendBtn.click();
        }
    });
});