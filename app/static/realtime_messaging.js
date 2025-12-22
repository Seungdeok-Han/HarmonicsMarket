/**
 * 실시간 메시징 기능 (WebSocket 기반)
 * Flask-SocketIO를 사용한 양방향 통신
 */

class RealtimeMessaging {
    constructor(otherId) {
        this.socket = io();
        this.otherId = otherId;
        this.isConnected = false;
        this.isTyping = false;
        
        this.init();
    }

    init() {
        console.log('🚀 실시간 메시징 초기화...');
        
        // 연결 이벤트
        this.socket.on('connect', () => {
            console.log('✅ 서버에 연결되었습니다');
            this.isConnected = true;
            this.joinConversation();
        });

        this.socket.on('disconnect', () => {
            console.log('❌ 서버 연결이 끊어졌습니다');
            this.isConnected = false;
        });

        // 메시지 수신
        this.socket.on('new_message', (data) => {
            console.log('💬 새 메시지 수신:', data);
            this.displayIncomingMessage(data);
            this.markMessageAsRead(data.id, data.sender_id);
        });

        // 메시지 전송 확인
        this.socket.on('message_sent', (data) => {
            console.log('✅ 메시지 전송됨:', data);
            this.displayOutgoingMessage(data);
        });

        // 메시지 읽음 상태
        this.socket.on('message_read', (data) => {
            console.log('👁️ 상대방이 메시지를 읽었습니다:', data);
            this.updateMessageReadStatus(data.message_id);
        });

        // 타이핑 상태
        this.socket.on('user_typing', (data) => {
            console.log('⌨️ 사용자 타이핑:', data);
            this.displayTypingIndicator(data);
        });

        // 에러
        this.socket.on('error', (data) => {
            console.error('❌ 오류:', data.message);
            alert('오류: ' + data.message);
        });

        // 전송 폼 이벤트
        this.setupFormEvents();
    }

    joinConversation() {
        /**대화방 입장*/
        if (this.otherId) {
            this.socket.emit('join_conversation', {
                other_id: this.otherId
            });
            console.log(`🚪 대화방 ${this.otherId} 입장`);
        }
    }

    leaveConversation() {
        /**대화방 퇴장*/
        if (this.otherId) {
            this.socket.emit('leave_conversation', {
                other_id: this.otherId
            });
            console.log(`🚪 대화방 ${this.otherId} 퇴장`);
        }
    }

    setupFormEvents() {
        /**폼 이벤트 설정*/
        const form = document.getElementById('message-form');
        const input = document.getElementById('message-input');

        if (!form || !input) {
            console.warn('⚠️ 메시지 폼을 찾을 수 없습니다');
            return;
        }

        // 폼 제출
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // 타이핑 표시
        input.addEventListener('input', () => {
            if (!this.isTyping) {
                this.isTyping = true;
                this.socket.emit('typing', {
                    recipient_id: this.otherId,
                    is_typing: true
                });
            }
        });

        // 타이핑 종료
        input.addEventListener('blur', () => {
            if (this.isTyping) {
                this.isTyping = false;
                this.socket.emit('typing', {
                    recipient_id: this.otherId,
                    is_typing: false
                });
            }
        });
    }

    sendMessage() {
        /**메시지 전송*/
        const input = document.getElementById('message-input');
        if (!input) return;

        const content = input.value.trim();
        if (!content) {
            alert('메시지를 입력하세요');
            return;
        }

        if (!this.isConnected) {
            alert('서버와의 연결이 끊어졌습니다. 페이지를 새로고침해주세요.');
            return;
        }

        // WebSocket으로 메시지 전송
        this.socket.emit('send_message', {
            recipient_id: this.otherId,
            content: content
        });

        // 입력창 초기화
        input.value = '';
        input.focus();

        // 타이핑 표시 종료
        if (this.isTyping) {
            this.isTyping = false;
            this.socket.emit('typing', {
                recipient_id: this.otherId,
                is_typing: false
            });
        }
    }

    displayIncomingMessage(data) {
        /**수신 메시지 표시*/
        const chatWindow = document.getElementById('chat-window');
        if (!chatWindow) {
            console.warn('⚠️ 채팅 창을 찾을 수 없습니다');
            return;
        }

        const messageEl = document.createElement('div');
        messageEl.className = 'message incoming';
        messageEl.id = `message-${data.id}`;
        messageEl.innerHTML = `
            <div class="message-content">
                <div class="message-bubble">
                    <p>${this.escapeHtml(data.content)}</p>
                    <small class="message-time">${data.created_at}</small>
                </div>
            </div>
        `;

        chatWindow.appendChild(messageEl);
        chatWindow.scrollTop = chatWindow.scrollHeight; // 자동 스크롤
    }

    displayOutgoingMessage(data) {
        /**발신 메시지 표시*/
        const chatWindow = document.getElementById('chat-window');
        if (!chatWindow) return;

        const messageEl = document.createElement('div');
        messageEl.className = 'message outgoing';
        messageEl.id = `message-${data.id}`;
        messageEl.innerHTML = `
            <div class="message-content">
                <div class="message-bubble">
                    <p>${this.escapeHtml(data.content)}</p>
                    <small class="message-time">${data.created_at}</small>
                </div>
            </div>
        `;

        chatWindow.appendChild(messageEl);
        chatWindow.scrollTop = chatWindow.scrollHeight; // 자동 스크롤
    }

    updateMessageReadStatus(messageId) {
        /**메시지 읽음 상태 업데이트*/
        const messageEl = document.getElementById(`message-${messageId}`);
        if (messageEl) {
            messageEl.classList.add('read');
            const timeEl = messageEl.querySelector('.message-time');
            if (timeEl) {
                timeEl.setAttribute('title', '읽음');
            }
        }
    }

    markMessageAsRead(messageId, senderId) {
        /**메시지 읽음 표시 (서버 전송)*/
        setTimeout(() => {
            this.socket.emit('mark_read', {
                message_id: messageId,
                sender_id: senderId
            });
        }, 500);
    }

    displayTypingIndicator(data) {
        /**타이핑 표시 표시*/
        const typingEl = document.getElementById('typing-indicator');
        if (!typingEl) return;

        if (data.is_typing) {
            typingEl.innerHTML = `
                <div class="typing-animation">
                    <span>${data.sender_name}이(가) 입력 중입니다</span>
                    <span class="typing-dots">
                        <span>.</span><span>.</span><span>.</span>
                    </span>
                </div>
            `;
            typingEl.style.display = 'block';
        } else {
            typingEl.style.display = 'none';
        }
    }

    escapeHtml(text) {
        /**XSS 방지*/
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    // URL에서 other_id 추출
    const pathParts = window.location.pathname.split('/');
    const otherId = parseInt(pathParts[pathParts.length - 1]);
    
    if (!isNaN(otherId)) {
        window.messaging = new RealtimeMessaging(otherId);
    }
});

// 페이지 언로드 시 대화방 퇴장
window.addEventListener('beforeunload', () => {
    if (window.messaging) {
        window.messaging.leaveConversation();
    }
});
