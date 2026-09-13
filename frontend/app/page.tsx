'use client';

import { useState, useEffect } from 'react';
import ChatHeader from './components/ChatHeader';
import ChatSidebar from './components/ChatSidebar';
import WelcomeSection from './components/WelcomeSection';
import ChatMessageList from './components/ChatMessageList';
import ChatInput from './components/ChatInput';
import type { Message, FontSize, Feedback, StoredConversation } from './types';

const CONV_STORAGE_KEY = 'saha-conversations';
const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

function getTime() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

function getDateStr() {
  return new Date().toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
}

function loadConversations(): StoredConversation[] {
  try { return JSON.parse(localStorage.getItem(CONV_STORAGE_KEY) ?? '[]'); } catch { return []; }
}

function saveConversations(convs: StoredConversation[]) {
  localStorage.setItem(CONV_STORAGE_KEY, JSON.stringify(convs.slice(0, 10)));
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [fontSize, setFontSize] = useState<FontSize>('normal');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [conversations, setConversations] = useState<StoredConversation[]>([]);

  // 초기 로드
  useEffect(() => {
    const savedDark = localStorage.getItem('darkMode');
    if (savedDark === 'true') { setIsDark(true); document.documentElement.classList.add('dark'); }
    const savedFont = localStorage.getItem('fontSize') as FontSize | null;
    if (savedFont) setFontSize(savedFont);
    setConversations(loadConversations());
  }, []);

  const toggleDark = () => {
    const next = !isDark;
    setIsDark(next);
    localStorage.setItem('darkMode', String(next));
    document.documentElement.classList.toggle('dark', next);
  };

  const setFontSizeAndSave = (size: FontSize) => {
    setFontSize(size);
    localStorage.setItem('fontSize', size);
  };

  // 현재 대화 저장 후 새 대화 시작
  const startNewConversation = () => {
    if (messages.length === 0) return;
    const firstUserMsg = messages.find(m => m.role === 'user');
    if (!firstUserMsg) return;

    const newConv: StoredConversation = {
      id: generateId(),
      title: firstUserMsg.content.slice(0, 28) + (firstUserMsg.content.length > 28 ? '...' : ''),
      date: getDateStr(),
      messages,
    };
    const updated = [newConv, ...conversations];
    setConversations(updated);
    saveConversations(updated);
    setMessages([]);
  };

  const loadConversation = (id: string) => {
    const conv = conversations.find(c => c.id === id);
    if (conv) setMessages(conv.messages);
  };

  const deleteConversation = (id: string) => {
    const updated = conversations.filter(c => c.id !== id);
    setConversations(updated);
    saveConversations(updated);
  };

  const updateFeedback = (id: string, feedback: Feedback) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, feedback } : m));
  };

  const sendMessage = async (text?: string) => {
    const msgText = (text ?? input).trim();
    if (!msgText || isLoading) return;

    const userMsg: Message = { id: generateId(), role: 'user', content: msgText, time: getTime() };
    const historyForApi = [...messages];
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    const botId = generateId();

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msgText,
          history: historyForApi.map(m => ({
            role: m.role === 'user' ? 'user' : 'assistant',
            content: m.content,
          })),
        }),
      });

      if (!res.ok) throw new Error('API 오류');

      const contentType = res.headers.get('content-type') ?? '';

      if (contentType.includes('text/event-stream') && res.body) {
        // ── SSE 스트리밍 모드 ──
        setMessages(prev => [...prev, { id: botId, role: 'bot', content: '', time: getTime(), isStreaming: true }]);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let accumulated = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop() ?? '';

          for (const chunk of chunks) {
            const dataLine = chunk.split('\n').find(l => l.startsWith('data: '));
            if (!dataLine) continue;
            const data = dataLine.slice(6).trim();
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.delta) {
                accumulated += parsed.delta;
                setMessages(prev => prev.map(m =>
                  m.id === botId ? { ...m, content: accumulated } : m
                ));
              }
            } catch {}
          }
        }
        setMessages(prev => prev.map(m => m.id === botId ? { ...m, isStreaming: false } : m));

      } else {
        // ── 일반 JSON 모드 (현재 백엔드) ──
        const data = await res.json();
        const answer = data.answer ?? '답변을 불러오지 못했습니다.';
        setMessages(prev => [...prev, { id: botId, role: 'bot', content: answer, time: getTime() }]);
      }

    } catch {
      setMessages(prev => [...prev, {
        id: botId, role: 'bot',
        content: '연결에 실패했습니다. 잠시 후 다시 시도해주세요.',
        time: getTime(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#f0f5fb] dark:bg-[#0d1117] transition-colors duration-300">

      {/* 헤더 */}
      <ChatHeader
        isDark={isDark}
        fontSize={fontSize}
        onToggleDark={toggleDark}
        onClearChat={startNewConversation}
        onSetFontSize={setFontSizeAndSave}
        onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
      />

      <div className="flex flex-1 overflow-hidden">

        {/* 사이드바 */}
        <ChatSidebar
          isLoading={isLoading}
          isMobileOpen={isMobileMenuOpen}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
          onSend={sendMessage}
          onNewConversation={startNewConversation}
          conversations={conversations}
          onLoadConversation={loadConversation}
          onDeleteConversation={deleteConversation}
        />

        {/* 메인 채팅 영역 */}
        <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
          {messages.length === 0 ? (
            <div className="flex-1 overflow-y-auto">
              <WelcomeSection onSend={sendMessage} isLoading={isLoading} />
            </div>
          ) : (
            <ChatMessageList
              messages={messages}
              isLoading={isLoading}
              fontSize={fontSize}
              onSend={sendMessage}
              onUpdateFeedback={updateFeedback}
            />
          )}

          {/* 입력창 */}
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={() => sendMessage()}
            isLoading={isLoading}
            fontSize={fontSize}
          />
        </div>
      </div>
    </div>
  );
}
