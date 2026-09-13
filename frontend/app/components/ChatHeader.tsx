'use client';

import { Moon, Sun, Trash2, Menu } from 'lucide-react';
import type { FontSize } from '../types';

type Props = {
  isDark: boolean;
  fontSize: FontSize;
  onToggleDark: () => void;
  onClearChat: () => void;
  onSetFontSize: (size: FontSize) => void;
  onOpenMobileMenu: () => void;
};

const fontSizes: { value: FontSize; label: string }[] = [
  { value: 'normal', label: '보통' },
  { value: 'large', label: '크게' },
  { value: 'largest', label: '아주 크게' },
];

export default function ChatHeader({
  isDark, fontSize, onToggleDark, onClearChat, onSetFontSize, onOpenMobileMenu,
}: Props) {
  return (
    <header className="shrink-0 bg-white dark:bg-[#111827] border-b border-gray-200 dark:border-gray-700/60 shadow-sm z-10">
      <div className="flex items-center justify-between px-4 lg:px-6 py-3">

        {/* 좌측: 햄버거(모바일) + 로고 + 서비스명 + 상태 뱃지 */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenMobileMenu}
            className="lg:hidden w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
            aria-label="메뉴 열기"
          >
            <Menu size={18} className="text-gray-600 dark:text-gray-400" />
          </button>

          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#004C97] flex items-center justify-center overflow-hidden shrink-0">
              <img src="/saharu.png" alt="사하루" className="w-full h-full object-contain" />
            </div>
            <div className="hidden sm:block">
              <p className="text-[14px] font-bold text-gray-900 dark:text-white leading-tight">
                사하구 AI 민원 도우미 사하루
              </p>
              <p className="text-[11px] text-gray-400 dark:text-gray-500">부산광역시 사하구청</p>
            </div>
            <div className="sm:hidden">
              <p className="text-[13px] font-bold text-gray-900 dark:text-white">사하루</p>
            </div>
          </div>

          {/* 운영 중 뱃지 */}
          <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700/50 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            운영 중
          </div>
        </div>

        {/* 우측: 접근성 도구 */}
        <div className="flex items-center gap-2">

          {/* 글자 크기 조절 (PC) */}
          <div className="hidden lg:flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
            <span className="text-[10px] text-gray-400 dark:text-gray-500 px-1.5 font-medium">글자</span>
            {fontSizes.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => onSetFontSize(value)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition ${
                  fontSize === value
                    ? 'bg-[#004C97] text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* 글자 크기 조절 (모바일 - 단일 토글) */}
          <button
            onClick={() => {
              const idx = fontSizes.findIndex(f => f.value === fontSize);
              onSetFontSize(fontSizes[(idx + 1) % fontSizes.length].value);
            }}
            className="lg:hidden w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition text-[10px] font-bold text-gray-600 dark:text-gray-400"
            title="글자 크기 변경"
          >
            가
          </button>

          {/* 다크모드 */}
          <button
            onClick={onToggleDark}
            title={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
            className="w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
          >
            {isDark
              ? <Sun size={16} className="text-yellow-500" />
              : <Moon size={16} className="text-gray-600" />}
          </button>

          {/* 새 대화 */}
          <button
            onClick={onClearChat}
            title="대화 내용 초기화"
            className="w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-500 transition text-gray-600 dark:text-gray-400"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </header>
  );
}
