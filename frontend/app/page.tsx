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

function getFakeReply(text: string) {
  if (text.includes('전입신고')) {
    return '전입신고는 정부24 또는 주민센터 방문을 통해 신청할 수 있습니다.';
  }
  if (text.includes('어린이집') || text.includes('보육')) {
    return '어린이집 관련 문의는 보육 담당 부서 또는 관련 민원 안내 페이지를 확인해주세요.';
  }
  if (text.includes('주차')) {
    return '주차 관련 민원은 정기주차, 불법주정차, 주차장 안내 등으로 나뉩니다.';
  }
  if (text.includes('폐기물') || text.includes('쓰레기')) {
    return '폐기물 배출은 품목과 배출 방식에 따라 달라집니다. 대형폐기물 여부도 함께 확인해 주세요.';
  }
  if (text.includes('증명서')) {
    return '증명서 발급은 정부24 또는 무인민원발급기, 주민센터 방문을 통해 가능한 경우가 많습니다.';
  }
  if (text.includes('보건소')) {
    return '보건소 업무는 예방접종, 검사, 건강관리 등으로 나뉘니 원하는 항목을 구체적으로 말씀해 주세요.';
  }
  if (text.includes('환경')) {
    return '환경·청소 민원은 배출, 수거, 불편 신고 등으로 나뉩니다.';
  }
  if (text.includes('담당 부서') || text.includes('담당부서')) {
    return '원하시는 민원명을 말씀해 주시면 관련 담당 부서를 찾는 데 도움이 되는 안내를 드릴 수 있습니다.';
  }

  return `입력하신 내용은 "${text}" 입니다.\n현재는 테스트용 화면이라 예시 답변을 보여주고 있습니다.`;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async (text?: string) => {
  const messageText = (text ?? input).trim();
  if (!messageText || loading) return;

  const userMessage: Message = { role: 'user', content: messageText };
  setMessages((prev) => [...prev, userMessage]);
  setInput('');
  setLoading(true);

  try {
    const res = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: messageText }),
    });
    if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
    const data = await res.json();
    const botMessage: Message = { role: 'bot', content: data.answer ?? '답변을 받지 못했습니다.' };
    setMessages((prev) => [...prev, botMessage]);
  } catch (err) {
    const errMessage: Message = { role: 'bot', content: `오류가 발생했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}` };
    setMessages((prev) => [...prev, errMessage]);
  } finally {
    setLoading(false);
  }
};

  return (
    <main className="min-h-screen bg-[#f5f6f8] px-3 py-4">
      <div className="mx-auto flex h-[92vh] w-full max-w-[430px] flex-col overflow-hidden rounded-[28px] border border-neutral-200 bg-white shadow-xl">
        {/* 헤더 */}
        <header className="flex items-center justify-between bg-[#f3bc12] px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-2xl shadow-sm">
              🐥
            </div>
            <div>
              <div className="text-[19px] font-extrabold text-black">사하구청 AI 민원 챗봇</div>
              <div className="text-[12px] text-neutral-800">민원 안내 테스트 화면</div>
            </div>
          </div>

          <div className="flex gap-2 text-[20px] text-[#9a4b1f]">
            <button type="button">📝</button>
            <button type="button">❓</button>
          </div>
        </header>

        {/* 본문 */}
        <section className="flex-1 overflow-y-auto bg-[#fcfbf7] px-3 pt-3 pb-20">
          <div className="rounded-[22px] border border-gray-200 bg-[#f9fafb] px-4 py-4 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-lg shadow-sm">
                🐥
              </div>
              <div className="text-[15px] font-extrabold text-neutral-900">사하구청 AI 민원 챗봇</div>
            </div>

            <div className="text-[14px] font-semibold leading-[1.6] text-neutral-900">
              사하구청 민원 챗봇입니다. 원하는 항목을 선택하거나 아래 입력창에 질문해 주세요.
            </div>

            <div className="mt-4 grid grid-cols-3 gap-3">
              {allMenus.map((item) => (
                <button
                  key={item.title}
                  onClick={() => sendMessage(item.question)}
                  className="flex min-h-[78px] flex-col items-center justify-center gap-1 rounded-[16px] border border-gray-200 bg-white px-2 py-3 shadow-sm transition hover:shadow-md"
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
            </div>
          )}
        </section>

        {/* 입력창 */}
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
            />

            <button
              onClick={() => sendMessage()}
              disabled={loading}
              className="rounded-full bg-[#3b82f6] px-3 py-1.5 text-[13px] font-bold text-white disabled:opacity-50"
            >
              {loading ? '...' : '전송'}
            </button>
          </div>
        </footer>
      </div>
    </main>
  );
}