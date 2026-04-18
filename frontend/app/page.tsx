'use client';

import { useState } from 'react';

type Message = {
  role: 'user' | 'bot';
  content: string;
};

type MenuItem = {
  title: string;
  icon: string;
  question: string;
};

const allMenus: MenuItem[] = [
  { title: '전입신고', icon: '🏠', question: '전입신고 방법 알려줘' },
  { title: '어린이집', icon: '🧒', question: '어린이집 관련 민원 알려줘' },
  { title: '복지지원', icon: '🧾', question: '복지 지원 민원 알려줘' },
  { title: '주차', icon: '🚗', question: '주차 관련 민원 안내해줘' },
  { title: '폐기물', icon: '🗑️', question: '폐기물 배출 방법 알려줘' },
  { title: '증명서', icon: '📄', question: '증명서 발급 방법 알려줘' },
  { title: '보건소', icon: '🏥', question: '보건소 업무 안내해줘' },
  { title: '환경민원', icon: '🌿', question: '환경 청소 관련 민원 알려줘' },
  { title: '담당부서', icon: '🏢', question: '담당 부서 찾는 방법 알려줘' },
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (text?: string) => {
    const messageText = (text ?? input).trim();
    if (!messageText || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: messageText,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: messageText }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();

      const botMessage: Message = {
        role: 'bot',
        content: data.answer ?? '답변을 불러오지 못했습니다.',
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'bot',
        content: '백엔드와 연결되지 않았거나 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#f5f6f8] px-3 py-4">
      <div className="mx-auto flex h-[92vh] w-full max-w-[430px] flex-col overflow-hidden rounded-[28px] border border-neutral-200 bg-white shadow-xl">
        <header className="flex items-center justify-between bg-[#f3bc12] px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-2xl shadow-sm">
              🐥
            </div>
            <div>
              <div className="text-[19px] font-extrabold text-black">
                사하구청 AI 민원 챗봇
              </div>
            </div>
          </div>

          <div className="flex gap-2 text-[20px] text-[#9a4b1f]">
            <button type="button">📝</button>
            <button type="button">❓</button>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto bg-[#fcfbf7] px-3 pt-3 pb-20">
          <div className="rounded-[22px] border border-gray-200 bg-[#f9fafb] px-4 py-4 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-lg shadow-sm">
                🐥
              </div>
              <div className="text-[15px] font-extrabold text-neutral-900">
                사하구청 AI 민원 챗봇
              </div>
            </div>

            <div className="text-[14px] font-semibold leading-[1.6] text-neutral-900">
              사하구청 민원 챗봇입니다. 원하는 항목을 선택하거나 아래 입력창에 질문해 주세요.
            </div>

            <div className="mt-4 grid grid-cols-3 gap-3">
              {allMenus.map((item) => (
                <button
                  key={item.title}
                  onClick={() => sendMessage(item.question)}
                  disabled={isLoading}
                  className="flex min-h-[78px] flex-col items-center justify-center gap-1 rounded-[16px] border border-gray-200 bg-white px-2 py-3 shadow-sm transition hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <div className="text-[22px]">{item.icon}</div>
                  <div className="break-keep text-center text-[12px] font-semibold leading-[1.25] text-neutral-900">
                    {item.title}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {messages.length > 0 && (
            <div className="mt-4 flex flex-col gap-2">
              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';

                return (
                  <div
                    key={idx}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[82%] whitespace-pre-wrap rounded-[18px] px-3 py-2 text-[14px] leading-[1.5] shadow-sm ${
                        isUser
                          ? 'bg-[#fff0b8] text-neutral-900'
                          : 'border border-gray-200 bg-white text-neutral-900'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[82%] rounded-[18px] border border-gray-200 bg-white px-3 py-2 text-[14px] leading-[1.5] text-gray-500 shadow-sm">
                    답변을 작성하고 있습니다... 잠시만 기다려주세요.
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <footer className="border-t border-neutral-200 bg-[#f3bc12] px-3 py-2.5">
          <div className="flex items-center gap-2 rounded-full bg-white px-3 py-2.5 shadow-md">
            <button type="button" className="text-[24px] text-[#f3bc12]">
              ↻
            </button>

            <input
              className="flex-1 bg-transparent text-[15px] text-black outline-none placeholder:text-neutral-400"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') sendMessage();
              }}
              placeholder="궁금한 내용을 입력해주세요"
              disabled={isLoading}
            />

            <button
              onClick={() => sendMessage()}
              disabled={isLoading}
              className="rounded-full bg-[#3b82f6] px-3 py-1.5 text-[13px] font-bold text-white disabled:cursor-not-allowed disabled:bg-[#93c5fd]"
            >
              {isLoading ? '답변 중...' : '전송'}
            </button>
          </div>
        </footer>
      </div>
    </main>
  );
}