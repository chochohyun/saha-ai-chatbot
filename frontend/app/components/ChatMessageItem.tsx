'use client';

import React, { useState } from 'react';
import { Copy, Check, ThumbsUp, ThumbsDown, ExternalLink } from 'lucide-react';
import type { Message, Feedback } from '../types';

const SUGGESTION_CHIPS = [
  '담당 부서 연락처 알려주세요',
  '신청에 필요한 서류가 뭔가요?',
  '온라인으로 신청할 수 있나요?',
  '처리 기간이 얼마나 걸리나요?',
];

// 인라인 파서: URL → 버튼, 전화번호 → tel: 버튼, **bold**
function parseInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const pattern = /(https?:\/\/[^\s]+)|(0\d{1,2}-\d{3,4}-\d{4})|(\*\*[^*]+\*\*)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(<span key={key++}>{text.slice(last, match.index)}</span>);
    }
    if (match[1]) {
      parts.push(
        <a key={key++} href={match[1]} target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[#004C97] dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-md px-2 py-0.5 text-[12px] font-medium hover:bg-blue-100 dark:hover:bg-blue-900/40 transition mx-0.5">
          <ExternalLink size={11} /> 관련 페이지 바로가기
        </a>
      );
    } else if (match[2]) {
      parts.push(
        <a key={key++} href={`tel:${match[2]}`}
          className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-md px-2 py-0.5 text-[12px] font-medium hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition mx-0.5">
          📞 {match[2]}
        </a>
      );
    } else if (match[3]) {
      parts.push(<strong key={key++} className="font-bold">{match[3].slice(2, -2)}</strong>);
    }
    last = pattern.lastIndex;
  }
  if (last < text.length) parts.push(<span key={key++}>{text.slice(last)}</span>);
  return parts.length > 0 ? parts : [<span key={0}>{text}</span>];
}

// 봇 메시지 본문 렌더러
function BotContent({ content, onSend, showChips }: {
  content: string;
  onSend: (q: string) => void;
  showChips: boolean;
}) {
  const lines = content.split('\n');
  const nodes: React.ReactNode[] = [];
  let key = 0;

  for (const line of lines) {
    const t = line.trim();
    if (!t) { nodes.push(<div key={key++} className="h-1" />); continue; }

    const numMatch = t.match(/^(\d+)\.\s+(.+)/);
    const bulletMatch = t.match(/^[-•]\s+(.+)/);
    const sourceMatch = t.match(/^📎\s*출처[:\s]+(.+)/);
    const h3Match = t.match(/^###\s+(.+)/);
    const h2Match = t.match(/^##\s+(.+)/);

    if (h2Match) {
      nodes.push(<p key={key++} className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mt-1">{parseInline(h2Match[1])}</p>);
    } else if (h3Match) {
      nodes.push(<p key={key++} className="text-[13px] font-bold text-gray-700 dark:text-gray-300 mt-1">{parseInline(h3Match[1])}</p>);
    } else if (numMatch) {
      nodes.push(
        <div key={key++} className="flex gap-2.5 bg-blue-50/70 dark:bg-blue-900/10 rounded-xl px-3 py-2.5 border border-blue-100 dark:border-blue-800/30">
          <span className="w-5 h-5 rounded-full bg-[#004C97] dark:bg-blue-600 text-white text-[10px] flex items-center justify-center shrink-0 mt-0.5 font-bold">
            {numMatch[1]}
          </span>
          <span className="leading-relaxed">{parseInline(numMatch[2])}</span>
        </div>
      );
    } else if (bulletMatch) {
      nodes.push(
        <div key={key++} className="flex gap-2 items-start pl-1">
          <span className="text-[#004C97] dark:text-blue-400 shrink-0 font-bold mt-0.5">·</span>
          <span className="leading-relaxed">{parseInline(bulletMatch[1])}</span>
        </div>
      );
    } else if (sourceMatch) {
      nodes.push(
        <div key={key++} className="flex flex-wrap items-center gap-1.5 pt-2 mt-1 border-t border-gray-100 dark:border-gray-700/50">
          <span className="text-[11px] text-gray-400 dark:text-gray-500">📎 출처</span>
          <span className="text-[12px]">{parseInline(sourceMatch[1])}</span>
        </div>
      );
    } else {
      nodes.push(<p key={key++} className="leading-relaxed">{parseInline(t)}</p>);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {nodes}
      {showChips && (
        <div className="flex flex-wrap gap-1.5 pt-3 mt-1 border-t border-gray-100 dark:border-gray-700/40">
          {SUGGESTION_CHIPS.map((chip) => (
            <button key={chip} onClick={() => onSend(chip)}
              className="text-[11px] text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700/60 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-[#004C97] dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 rounded-full px-3 py-1 transition">
              {chip}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

type Props = {
  msg: Message;
  isLastBot: boolean;
  onSend: (text: string) => void;
  onUpdateFeedback: (id: string, feedback: Feedback) => void;
};

export default function ChatMessageItem({ msg, isLastBot, onSend, onUpdateFeedback }: Props) {
  const isUser = msg.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>

      {/* 봇 아바타 */}
      {!isUser && (
        <div className="w-9 h-9 rounded-2xl bg-white dark:bg-[#1c2333] border border-gray-100 dark:border-gray-700 flex items-center justify-center shrink-0 mt-0.5 shadow-sm overflow-hidden">
          <img src="/saharu.png" alt="사하루" className="w-full h-full object-contain" />
        </div>
      )}

      <div className={`flex flex-col gap-1.5 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* 말풍선 */}
        <div className={`px-4 py-3 leading-relaxed shadow-sm ${
          isUser
            ? 'bg-[#004C97] text-white rounded-[18px] rounded-br-[4px] whitespace-pre-wrap'
            : 'bg-white dark:bg-[#1c2333] text-gray-800 dark:text-gray-100 border border-gray-100 dark:border-gray-700/50 rounded-[18px] rounded-bl-[4px]'
        }`}>
          {isUser ? (
            msg.content
          ) : msg.isStreaming ? (
            <span className="whitespace-pre-wrap">{msg.content}<span className="inline-block w-0.5 h-4 bg-gray-400 dark:bg-gray-500 animate-pulse ml-0.5 align-text-bottom" /></span>
          ) : (
            <BotContent content={msg.content} onSend={onSend} showChips={isLastBot} />
          )}
        </div>

        {/* 타임스탬프 + 액션 버튼 (봇 메시지만) */}
        <div className={`flex items-center gap-2 px-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <span className="text-[11px] text-gray-400 dark:text-gray-600">{msg.time}</span>

          {!isUser && !msg.isStreaming && (
            <div className="flex items-center gap-1">
              {/* 복사 */}
              <button
                onClick={handleCopy}
                title="답변 복사"
                className="w-6 h-6 flex items-center justify-center rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
              >
                {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
              </button>

              {/* 피드백 */}
              <button
                onClick={() => onUpdateFeedback(msg.id, msg.feedback === 'good' ? null : 'good')}
                title="도움이 됐어요"
                className={`w-6 h-6 flex items-center justify-center rounded-md transition ${
                  msg.feedback === 'good'
                    ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-500'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-emerald-500'
                }`}
              >
                <ThumbsUp size={11} />
              </button>
              <button
                onClick={() => onUpdateFeedback(msg.id, msg.feedback === 'bad' ? null : 'bad')}
                title="아쉬워요"
                className={`w-6 h-6 flex items-center justify-center rounded-md transition ${
                  msg.feedback === 'bad'
                    ? 'bg-red-50 dark:bg-red-900/30 text-red-500'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-red-500'
                }`}
              >
                <ThumbsDown size={11} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 유저 아바타 */}
      {isUser && (
        <div className="w-9 h-9 rounded-2xl bg-blue-100 dark:bg-blue-900/40 border border-blue-200 dark:border-blue-800 flex items-center justify-center text-base shrink-0 mt-0.5">
          👤
        </div>
      )}
    </div>
  );
}
