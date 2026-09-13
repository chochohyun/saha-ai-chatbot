'use client';

import { useEffect, useRef } from 'react';
import ChatMessageItem from './ChatMessageItem';
import type { Message, Feedback, FontSize } from '../types';

type Props = {
  messages: Message[];
  isLoading: boolean;
  fontSize: FontSize;
  onSend: (text: string) => void;
  onUpdateFeedback: (id: string, feedback: Feedback) => void;
};

const fontSizePxMap: Record<FontSize, number> = {
  normal: 14,
  large: 16,
  largest: 18,
};

export default function ChatMessageList({ messages, isLoading, fontSize, onSend, onUpdateFeedback }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // 마지막 봇 메시지 인덱스
  const lastBotIdx = messages.map((m, i) => (m.role === 'bot' ? i : -1)).filter(i => i >= 0).at(-1) ?? -1;

  return (
    <section
      className="flex-1 overflow-y-auto px-4 lg:px-6 py-6"
      style={{ fontSize: `${fontSizePxMap[fontSize]}px` }}
    >
      <div className="flex flex-col gap-5 max-w-3xl mx-auto">
        {messages.map((msg, idx) => (
          <ChatMessageItem
            key={msg.id}
            msg={msg}
            isLastBot={idx === lastBotIdx && !isLoading}
            onSend={onSend}
            onUpdateFeedback={onUpdateFeedback}
          />
        ))}

        {/* 로딩 표시 (스트리밍 시작 전) */}
        {isLoading && messages[messages.length - 1]?.role !== 'bot' && (
          <div className="flex gap-3 justify-start">
            <div className="w-9 h-9 rounded-2xl bg-white dark:bg-[#1c2333] border border-gray-100 dark:border-gray-700 flex items-center justify-center shrink-0 shadow-sm overflow-hidden">
              <img src="/saharu.png" alt="사하루" className="w-full h-full object-contain" />
            </div>
            <div className="bg-white dark:bg-[#1c2333] border border-gray-100 dark:border-gray-700/50 rounded-[18px] rounded-bl-[4px] px-5 py-4 shadow-sm">
              <div className="flex gap-1.5 items-center h-4">
                <span className="w-2 h-2 rounded-full bg-[#004C97] dark:bg-blue-400 animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 rounded-full bg-[#004C97] dark:bg-blue-400 animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 rounded-full bg-[#004C97] dark:bg-blue-400 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </section>
  );
}
