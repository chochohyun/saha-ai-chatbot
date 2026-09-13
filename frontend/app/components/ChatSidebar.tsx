'use client';

import { MessageSquarePlus, ChevronRight, Clock, Phone, X, Trash2 } from 'lucide-react';
import type { StoredConversation } from '../types';

const TOP_QUESTIONS = [
  { icon: '🗑️', label: '대형폐기물 배출', q: '대형 폐기물 배출 스티커 안내해주세요' },
  { icon: '🏠', label: '주민등록 전입신고', q: '주민등록 전입신고 방법을 알려주세요' },
  { icon: '🚗', label: '불법주정차 단속', q: '불법 주정차 단속 및 신고 방법을 알려주세요' },
  { icon: '👶', label: '출산·양육 혜택', q: '출산 지원금 및 영유아 혜택이 뭐가 있나요?' },
  { icon: '📘', label: '여권 발급 안내', q: '여권 처음 만들려면 뭐가 필요한가요?' },
];

type Props = {
  isLoading: boolean;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
  onSend: (text: string) => void;
  onNewConversation: () => void;
  conversations: StoredConversation[];
  onLoadConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
};

function SidebarContent({
  isLoading, onSend, onNewConversation, conversations, onLoadConversation, onDeleteConversation, onClose,
}: Props & { onClose?: () => void }) {
  return (
    <div className="flex flex-col h-full">

      {/* 로고 헤더 */}
      <div className="bg-[#004C97] px-5 py-5 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white/20 flex items-center justify-center overflow-hidden shrink-0">
              <img src="/saharu.png" alt="사하루" className="w-full h-full object-contain" />
            </div>
            <div>
              <p className="text-[15px] font-bold text-white leading-tight">사하구청</p>
              <p className="text-[11px] text-blue-200">AI 민원 안내 서비스</p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/15 hover:bg-white/25 text-white transition"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* 스크롤 영역 */}
      <div className="flex-1 overflow-y-auto px-4 py-5 flex flex-col gap-5">

        {/* 새 대화 시작 버튼 */}
        <button
          onClick={onNewConversation}
          className="flex items-center justify-center gap-2 w-full rounded-xl bg-[#004C97] hover:bg-[#003d80] text-white text-[13px] font-semibold py-3 transition-all active:scale-95 shadow-sm"
        >
          <MessageSquarePlus size={16} />
          새 대화 시작
        </button>

        {/* 자주 찾는 민원 Top 5 */}
        <div>
          <p className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-2.5 px-0.5">
            자주 찾는 민원 Top 5
          </p>
          <div className="flex flex-col gap-1">
            {TOP_QUESTIONS.map((item) => (
              <button
                key={item.label}
                onClick={() => { onSend(item.q); onClose?.(); }}
                disabled={isLoading}
                className="flex items-center gap-2.5 text-left rounded-xl px-3 py-2.5 bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 hover:border-[#004C97] dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all disabled:opacity-40 group"
              >
                <span className="text-[16px] shrink-0">{item.icon}</span>
                <span className="flex-1 text-[12px] font-medium text-gray-700 dark:text-gray-300 group-hover:text-[#004C97] dark:group-hover:text-blue-400 leading-tight break-keep">
                  {item.label}
                </span>
                <ChevronRight size={14} className="text-gray-300 dark:text-gray-600 group-hover:text-[#004C97] dark:group-hover:text-blue-400 shrink-0" />
              </button>
            ))}
          </div>
        </div>

        {/* 최근 문의 내역 */}
        {conversations.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2.5 px-0.5">
              <Clock size={12} className="text-gray-400 dark:text-gray-500" />
              <p className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
                최근 문의 내역
              </p>
            </div>
            <div className="flex flex-col gap-1">
              {conversations.slice(0, 5).map((conv) => (
                <div key={conv.id} className="flex items-center gap-1 group">
                  <button
                    onClick={() => { onLoadConversation(conv.id); onClose?.(); }}
                    className="flex-1 text-left rounded-xl px-3 py-2.5 bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
                  >
                    <p className="text-[12px] font-medium text-gray-700 dark:text-gray-300 truncate leading-tight">{conv.title}</p>
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">{conv.date}</p>
                  </button>
                  <button
                    onClick={() => onDeleteConversation(conv.id)}
                    className="w-7 h-7 flex items-center justify-center rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-all"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* 하단 콜센터 안내 */}
      <div className="px-4 pb-4 shrink-0">
        <div className="rounded-2xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/40 px-4 py-4">
          <div className="flex items-center gap-2.5 mb-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#004C97] flex items-center justify-center shrink-0">
              <Phone size={14} className="text-white" />
            </div>
            <div>
              <p className="text-[13px] font-bold text-gray-800 dark:text-gray-100">051-220-4000</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">민원 콜센터</p>
            </div>
          </div>
          <div className="flex flex-col gap-0.5 text-[11px] text-gray-500 dark:text-gray-400 pl-0.5">
            <span>🕐 평일 09:00 ~ 18:00</span>
            <span>📍 낙동대로398번길 12</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatSidebar(props: Props) {
  return (
    <>
      {/* 모바일 오버레이 */}
      <div
        className={`lg:hidden fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 ${
          props.isMobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={props.onCloseMobile}
      />

      {/* 모바일 드로어 */}
      <aside
        className={`lg:hidden fixed left-0 top-0 h-full w-80 bg-white dark:bg-[#111827] z-50 shadow-2xl transform transition-transform duration-300 ${
          props.isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <SidebarContent {...props} onClose={props.onCloseMobile} />
      </aside>

      {/* PC 사이드바 */}
      <aside className="hidden lg:flex w-80 flex-col bg-white dark:bg-[#111827] border-r border-gray-200 dark:border-gray-700/60 shrink-0 shadow-lg">
        <SidebarContent {...props} />
      </aside>
    </>
  );
}
