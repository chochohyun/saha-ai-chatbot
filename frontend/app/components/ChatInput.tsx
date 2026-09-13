'use client';

import { useRef, useEffect, useState } from 'react';
import { Send, Mic, MicOff, X } from 'lucide-react';
import type { FontSize } from '../types';

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
  fontSize: FontSize;
};

const fontSizePxMap: Record<FontSize, number> = {
  normal: 14,
  large: 16,
  largest: 18,
};

export default function ChatInput({ value, onChange, onSend, isLoading, fontSize }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  // 높이 자동 조절
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && value.trim()) onSend();
    }
  };

  const toggleSTT = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      alert('이 브라우저에서는 음성 인식을 지원하지 않습니다.\nChrome 또는 Edge 브라우저를 사용해주세요.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const rec = new SR();
    rec.lang = 'ko-KR';
    rec.continuous = false;
    rec.interimResults = false;

    rec.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript;
      onChange(value + (value ? ' ' : '') + transcript);
      setIsListening(false);
    };
    rec.onerror = () => setIsListening(false);
    rec.onend = () => setIsListening(false);

    rec.start();
    recognitionRef.current = rec;
    setIsListening(true);
  };

  const canSend = !isLoading && value.trim().length > 0;

  return (
    <footer className="shrink-0 bg-white dark:bg-[#111827] border-t border-gray-200 dark:border-gray-700/60 px-4 lg:px-6 py-3">
      <div className="max-w-3xl mx-auto flex flex-col gap-2">
        <div className="flex gap-2 items-end">

          {/* 텍스트 입력창 */}
          <div className={`flex-1 flex items-end gap-2 rounded-2xl bg-gray-50 dark:bg-[#1c2333] border ${
            isListening
              ? 'border-red-400 dark:border-red-500'
              : 'border-gray-200 dark:border-gray-700/50 focus-within:border-[#004C97] dark:focus-within:border-blue-500'
          } px-4 py-3 transition-colors`}>
            <textarea
              ref={textareaRef}
              rows={1}
              className="flex-1 bg-transparent text-gray-800 dark:text-gray-100 outline-none placeholder:text-gray-400 dark:placeholder:text-gray-500 resize-none leading-relaxed"
              style={{ fontSize: `${fontSizePxMap[fontSize]}px` }}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isListening ? '🎤 듣고 있어요...' : '궁금한 민원 내용을 입력해주세요...'}
              disabled={isLoading}
            />

            {/* 지우기 버튼 */}
            {value && (
              <button
                onClick={() => onChange('')}
                className="mb-0.5 w-5 h-5 flex items-center justify-center rounded-full bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500 text-white transition shrink-0"
              >
                <X size={11} />
              </button>
            )}
          </div>

          {/* 음성 인식(STT) */}
          <button
            onClick={toggleSTT}
            title={isListening ? '음성 인식 중지' : '음성으로 입력 (고령층 접근성)'}
            className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all shrink-0 ${
              isListening
                ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400'
            }`}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

          {/* 전송 버튼 */}
          <button
            onClick={onSend}
            disabled={!canSend}
            title="전송 (Enter)"
            className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all shrink-0 shadow-sm ${
              canSend
                ? 'bg-[#004C97] hover:bg-[#003d80] text-white active:scale-95'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
            }`}
          >
            <Send size={17} />
          </button>
        </div>

        {/* 안내 캡션 */}
        <p className="text-[10px] text-gray-400 dark:text-gray-600 text-center">
          AI 답변은 사하구청 공공데이터를 기반으로 생성되며, 법적 효력은 행정기관 확인이 필요합니다.
        </p>
      </div>
    </footer>
  );
}
