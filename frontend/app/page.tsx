'use client';

import { useState, useEffect } from 'react';
import ChatHeader from './components/ChatHeader';
import ChatSidebar from './components/ChatSidebar';
import WelcomeSection from './components/WelcomeSection';
import ChatMessageList from './components/ChatMessageList';
import ChatInput from './components/ChatInput';
import FeedbackAdminModal from './components/FeedbackAdminModal';
import type { Message, FontSize, Feedback, StoredConversation, ApiSession, ApiMessage } from './types';

const API_BASE = 'http://127.0.0.1:8000';
const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

function getTime() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

function sessionToConversation(s: ApiSession): StoredConversation {
  return {
    id: s.session_id,
    title: s.title ?? '제목 없음',
    date: new Date(s.updated_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
    messages: [],
  };
}

function apiMessageToMessage(m: ApiMessage): Message {
  return {
    id: String(m.message_id),
    messageId: m.message_id,
    role: m.sender === 'user' ? 'user' : 'bot',
    content: m.content,
    time: new Date(m.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
    feedback: m.feedback,
  };
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [fontSize, setFontSize] = useState<FontSize>('normal');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [conversations, setConversations] = useState<StoredConversation[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isAdminOpen, setIsAdminOpen] = useState(false);

  // ── 세션 목록 API 조회 ────────────────────────────────────────────────────
  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      if (!res.ok) return;
      const data: ApiSession[] = await res.json();
      setConversations(data.map(sessionToConversation));
    } catch {}
  };

  // 초기 로드
  useEffect(() => {
    const savedDark = localStorage.getItem('darkMode');
    if (savedDark === 'true') { setIsDark(true); document.documentElement.classList.add('dark'); }
    const savedFont = localStorage.getItem('fontSize') as FontSize | null;
    if (savedFont) setFontSize(savedFont);
    fetchSessions();
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

  // ── 새 대화 시작 ───────────────────────────────────────────────────────────
  const startNewConversation = () => {
    setCurrentSessionId(null);
    setMessages([]);
    fetchSessions();
  };

  // ── 세션 대화 이력 불러오기 ────────────────────────────────────────────────
  const loadConversation = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${id}/messages`);
      if (!res.ok) return;
      const data: ApiMessage[] = await res.json();
      setMessages(data.map(apiMessageToMessage));
      setCurrentSessionId(id);
    } catch {}
  };

  // ── 세션 삭제 (로컬 목록에서만 제거) ────────────────────────────────────────
  const deleteConversation = (id: string) => {
    setConversations(prev => prev.filter(c => c.id !== id));
    if (currentSessionId === id) {
      setCurrentSessionId(null);
      setMessages([]);
    }
  };

  // ── 피드백 업데이트 ───────────────────────────────────────────────────────
  const updateFeedback = async (id: string, feedback: Feedback) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, feedback } : m));

    const msg = messages.find(m => m.id === id);
    if (!msg?.messageId || !feedback) return;

    try {
      await fetch(`${API_BASE}/api/messages/${msg.messageId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback }),
      });
    } catch {}
  };

  // ── 메시지 전송 ───────────────────────────────────────────────────────────
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
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msgText,
          history: historyForApi.map(m => ({
            role: m.role === 'user' ? 'user' : 'assistant',
            content: m.content,
          })),
          session_id: currentSessionId,
        }),
      });

      if (!res.ok) throw new Error('API 오류');

      const contentType = res.headers.get('content-type') ?? '';

      if (contentType.includes('text/event-stream') && res.body) {
        // ── SSE 스트리밍 모드 ──────────────────────────────────────────────
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
            const raw = dataLine.slice(6).trim();
            if (raw === '[DONE]') continue;

            try {
              const parsed = JSON.parse(raw);

              if (parsed.delta) {
                accumulated += parsed.delta;
                setMessages(prev => prev.map(m =>
                  m.id === botId ? { ...m, content: accumulated } : m
                ));
              }

              // session_id 수신 시 세션 추적 시작
              if (parsed.session_id) {
                setCurrentSessionId(parsed.session_id);
              }

              // 완료 이벤트: message_id 저장 + 사이드바 갱신
              if (parsed.done) {
                setMessages(prev => prev.map(m =>
                  m.id === botId
                    ? { ...m, messageId: parsed.message_id, isStreaming: false }
                    : m
                ));
                fetchSessions();
              }
            } catch {}
          }
        }

        // 스트림 종료 후 isStreaming 보장
        setMessages(prev => prev.map(m =>
          m.id === botId && m.isStreaming ? { ...m, isStreaming: false } : m
        ));

      } else {
        // ── 일반 JSON 모드 ─────────────────────────────────────────────────
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
          onOpenAdmin={() => setIsAdminOpen(true)}
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

      {/* 피드백 관리자 모달 */}
      {isAdminOpen && (
        <FeedbackAdminModal apiBase={API_BASE} onClose={() => setIsAdminOpen(false)} />
      )}
    </div>
  );
}
