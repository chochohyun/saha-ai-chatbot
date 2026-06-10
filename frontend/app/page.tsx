'use client';

import { useState, useEffect, useRef } from 'react';

type Message = {
  role: 'user' | 'bot';
  content: string;
  time: string;
};

type MenuItem = {
  title: string;
  icon: string;
  question: string;
};

const allMenus: MenuItem[] = [
  { title: '어린이집', icon: '🧒', question: '어린이집 관련 민원 알려줘' },
  { title: '복지지원', icon: '🧾', question: '복지 지원 민원 알려줘' },
  { title: '주차', icon: '🚗', question: '주차 관련 민원 안내해줘' },
  { title: '폐기물', icon: '🗑️', question: '폐기물 배출 방법 알려줘' },
  { title: '증명서', icon: '📄', question: '증명서 발급 방법 알려줘' },
  { title: '보건소', icon: '🏥', question: '보건소 업무 안내해줘' },
  { title: '환경민원', icon: '🌿', question: '환경 청소 관련 민원 알려줘' },
  { title: '담당부서', icon: '🏢', question: '담당 부서 찾는 방법 알려줘' },
  { title: '여권', icon: '📘', question: '여권 발급 방법 알려줘' },
];

function getTime() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem('darkMode');
    if (saved === 'true') {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const toggleDark = () => {
    const next = !isDark;
    setIsDark(next);
    localStorage.setItem('darkMode', String(next));
    document.documentElement.classList.toggle('dark', next);
  };

  const sendMessage = async (text?: string) => {
    const messageText = (text ?? input).trim();
    if (!messageText || isLoading) return;

    const userMsg: Message = { role: 'user', content: messageText, time: getTime() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          history: messages.map((m) => ({
            role: m.role === 'user' ? 'user' : 'assistant',
            content: m.content,
          })),
        }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: data.answer ?? '답변을 불러오지 못했습니다.', time: getTime() },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: '연결에 실패했습니다. 잠시 후 다시 시도해주세요.', time: getTime() },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f0f5fb] dark:bg-[#0d1117] transition-colors duration-300">

      {/* ── 사이드바 (PC 전용) ── */}
      <aside className="hidden lg:flex w-72 flex-col bg-[#004C97] dark:bg-[#0a1929] text-white shrink-0 shadow-xl">

        {/* 로고 */}
        <div className="px-6 py-7 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-white/15 flex items-center justify-center text-2xl shrink-0">
              🏛️
            </div>
            <div>
              <p className="text-[17px] font-bold leading-tight">사하구청</p>
              <p className="text-[12px] text-blue-200 mt-0.5">AI 민원 안내 서비스</p>
            </div>
          </div>
          <p className="text-[12px] text-blue-300 leading-relaxed mt-4">
            사하구 민원 정보를 빠르게 안내해드립니다.<br />
            궁금한 내용을 입력하거나 항목을 선택하세요.
          </p>
        </div>

        {/* 빠른 메뉴 */}
        <div className="flex-1 px-4 py-5 overflow-y-auto">
          <p className="text-[10px] font-semibold text-blue-300 uppercase tracking-widest mb-3 px-1">
            빠른 민원 안내
          </p>
          <div className="grid grid-cols-3 gap-2">
            {allMenus.map((item) => (
              <button
                key={item.title}
                onClick={() => sendMessage(item.question)}
                disabled={isLoading}
                className="flex flex-col items-center gap-1.5 rounded-xl bg-white/10 hover:bg-white/20 active:scale-95 px-1.5 py-3 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span className="text-[22px]">{item.icon}</span>
                <span className="text-[11px] font-medium text-center leading-tight break-keep">
                  {item.title}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* 하단 컨트롤 */}
        <div className="px-5 py-4 border-t border-white/10 flex items-center justify-between">
          <button
            onClick={() => setMessages([])}
            className="flex items-center gap-1.5 text-[12px] text-blue-300 hover:text-white transition"
          >
            <span className="text-sm">🗑️</span> 대화 초기화
          </button>
          <button
            onClick={toggleDark}
            title={isDark ? '라이트 모드' : '다크 모드'}
            className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-base transition"
          >
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>
      </aside>

      {/* ── 메인 영역 ── */}
      <div className="flex flex-1 flex-col min-w-0">

        {/* 모바일 헤더 */}
        <header className="lg:hidden flex items-center justify-between bg-[#004C97] dark:bg-[#0a1929] px-4 py-3 text-white shrink-0 shadow-md">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🏛️</span>
            <span className="text-[15px] font-bold">사하구청 AI 민원 챗봇</span>
          </div>
          <div className="flex gap-1.5">
            <button
              onClick={() => setMessages([])}
              className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/15 hover:bg-white/25 text-sm transition"
            >
              🗑️
            </button>
            <button
              onClick={toggleDark}
              className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/15 hover:bg-white/25 text-sm transition"
            >
              {isDark ? '☀️' : '🌙'}
            </button>
          </div>
        </header>

        {/* PC 채팅 헤더 */}
        <header className="hidden lg:flex items-center justify-between bg-white dark:bg-[#111827] border-b border-gray-200 dark:border-gray-700/60 px-8 py-4 shrink-0">
          <div>
            <h1 className="text-[16px] font-bold text-gray-900 dark:text-white">민원 안내 채팅</h1>
            <p className="text-[12px] text-gray-400 dark:text-gray-500 mt-0.5">
              질문을 입력하면 관련 민원 정보를 안내해드립니다
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-[12px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse inline-block" />
            서비스 운영 중
          </div>
        </header>

        {/* 메시지 영역 */}
        <section className="flex-1 overflow-y-auto px-4 lg:px-10 py-6">

          {/* 빈 상태 */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
              <div className="w-20 h-20 rounded-3xl bg-[#004C97]/10 dark:bg-[#004C97]/25 flex items-center justify-center text-4xl">
                🏛️
              </div>
              <div>
                <p className="text-[18px] font-bold text-gray-800 dark:text-gray-100">
                  무엇을 도와드릴까요?
                </p>
                <p className="text-[13px] text-gray-400 dark:text-gray-500 mt-1.5 leading-relaxed">
                  민원 정보, 복지 지원, 증명서 발급 등을<br />안내해드립니다
                </p>
              </div>

              {/* 모바일 빠른 메뉴 */}
              <div className="lg:hidden grid grid-cols-3 gap-2 w-full max-w-xs mt-1">
                {allMenus.map((item) => (
                  <button
                    key={item.title}
                    onClick={() => sendMessage(item.question)}
                    disabled={isLoading}
                    className="flex flex-col items-center gap-1.5 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1c2333] px-2 py-3 shadow-sm hover:shadow-md hover:border-[#004C97] dark:hover:border-[#004C97] transition-all disabled:opacity-50"
                  >
                    <span className="text-xl">{item.icon}</span>
                    <span className="text-[11px] font-medium text-gray-700 dark:text-gray-300 leading-tight break-keep text-center">
                      {item.title}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 메시지 목록 */}
          <div className="flex flex-col gap-5 max-w-3xl mx-auto">
            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              return (
                <div key={idx} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>

                  {/* 봇 아바타 */}
                  {!isUser && (
                    <div className="w-9 h-9 rounded-2xl bg-[#004C97] flex items-center justify-center text-white text-base shrink-0 mt-0.5 shadow-sm">
                      🏛️
                    </div>
                  )}

                  <div className={`flex flex-col gap-1 max-w-[78%] ${isUser ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`px-4 py-3 text-[14px] leading-relaxed whitespace-pre-wrap shadow-sm ${
                        isUser
                          ? 'bg-[#004C97] text-white rounded-2xl rounded-br-md'
                          : 'bg-white dark:bg-[#1c2333] text-gray-800 dark:text-gray-100 border border-gray-100 dark:border-gray-700/50 rounded-2xl rounded-bl-md'
                      }`}
                    >
                      {msg.content}
                    </div>
                    <span className="text-[11px] text-gray-400 dark:text-gray-600 px-1">
                      {msg.time}
                    </span>
                  </div>

                  {/* 유저 아바타 */}
                  {isUser && (
                    <div className="w-9 h-9 rounded-2xl bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-base shrink-0 mt-0.5">
                      👤
                    </div>
                  )}
                </div>
              );
            })}

            {/* 로딩 (점 3개 bounce) */}
            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="w-9 h-9 rounded-2xl bg-[#004C97] flex items-center justify-center text-white text-base shrink-0 mt-0.5 shadow-sm">
                  🏛️
                </div>
                <div className="bg-white dark:bg-[#1c2333] border border-gray-100 dark:border-gray-700/50 rounded-2xl rounded-bl-md px-5 py-4 shadow-sm">
                  <div className="flex gap-1.5 items-center h-4">
                    <span className="w-2 h-2 rounded-full bg-[#004C97] dark:bg-blue-400 animate-bounce [animation-delay:0ms]" />
                    <span className="w-2 h-2 rounded-full bg-[#004C97] dark:bg-blue-400 animate-bounce [animation-delay:150ms]" />
                    <span className="w-2 h-2 rounded-full bg-[#004C97] dark:bg-blue-400 animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </section>

        {/* 입력창 */}
        <footer className="shrink-0 bg-white dark:bg-[#111827] border-t border-gray-200 dark:border-gray-700/60 px-4 lg:px-10 py-4">
          <div className="flex gap-3 items-center max-w-3xl mx-auto">
            <div className="flex-1 flex items-center gap-2 rounded-2xl bg-gray-50 dark:bg-[#1c2333] border border-gray-200 dark:border-gray-700/50 px-4 py-3 focus-within:border-[#004C97] dark:focus-within:border-blue-500 transition-colors">
              <input
                className="flex-1 bg-transparent text-[14px] text-gray-800 dark:text-gray-100 outline-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="궁금한 민원 내용을 입력해주세요..."
                disabled={isLoading}
              />
            </div>
            <button
              onClick={() => sendMessage()}
              disabled={isLoading || !input.trim()}
              className="w-11 h-11 rounded-xl bg-[#004C97] hover:bg-[#003d80] disabled:bg-gray-200 dark:disabled:bg-gray-700 text-white flex items-center justify-center transition-all active:scale-95 shrink-0 shadow-sm"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <p className="text-[11px] text-gray-400 dark:text-gray-600 text-center mt-2.5">
            부산광역시 사하구청 공식 AI 민원 안내 서비스
          </p>
        </footer>
      </div>
    </div>
  );
}
