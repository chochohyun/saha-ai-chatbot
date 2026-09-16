'use client';

import { useState } from 'react';
import { X, ThumbsUp, ThumbsDown, BarChart2, ChevronDown, ChevronRight, Loader2, Lock, Eye, EyeOff } from 'lucide-react';
import type { ApiSession, ApiMessage } from '../types';

const ADMIN_PW = process.env.NEXT_PUBLIC_ADMIN_PASSWORD ?? 'saha-admin-2024';

type SessionStat = {
  session: ApiSession;
  messages: ApiMessage[];
  likes: number;
  dislikes: number;
};

type Props = {
  apiBase: string;
  onClose: () => void;
};

// ── 비밀번호 입력 화면 ─────────────────────────────────────────────────────────
function PasswordGate({ onSuccess }: { onSuccess: () => void }) {
  const [pw, setPw] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pw === ADMIN_PW) {
      sessionStorage.setItem('admin_auth', 'true');
      onSuccess();
    } else {
      setError(true);
      setPw('');
      setTimeout(() => setError(false), 2000);
    }
  };

  return (
    <div className="flex flex-col items-center gap-5 py-10 px-6">
      <div className="w-14 h-14 rounded-2xl bg-[#004C97] flex items-center justify-center">
        <Lock size={24} className="text-white" />
      </div>
      <div className="text-center">
        <p className="text-[15px] font-bold text-gray-900 dark:text-white">관리자 인증</p>
        <p className="text-[12px] text-gray-400 dark:text-gray-500 mt-1">관리자 비밀번호를 입력하세요</p>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-xs flex flex-col gap-3">
        <div className="relative">
          <input
            type={show ? 'text' : 'password'}
            value={pw}
            onChange={e => setPw(e.target.value)}
            placeholder="비밀번호"
            autoFocus
            className={`w-full px-4 py-2.5 pr-10 rounded-xl border text-[13px] bg-white dark:bg-gray-800 text-gray-900 dark:text-white outline-none transition ${
              error
                ? 'border-red-400 dark:border-red-500 animate-pulse'
                : 'border-gray-200 dark:border-gray-700 focus:border-[#004C97] dark:focus:border-blue-500'
            }`}
          />
          <button
            type="button"
            onClick={() => setShow(v => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
          >
            {show ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>

        {error && (
          <p className="text-[12px] text-red-500 dark:text-red-400 text-center">
            비밀번호가 올바르지 않습니다.
          </p>
        )}

        <button
          type="submit"
          className="w-full bg-[#004C97] hover:bg-[#003d80] text-white text-[13px] font-semibold py-2.5 rounded-xl transition"
        >
          확인
        </button>
      </form>
    </div>
  );
}

// ── 통계 화면 ──────────────────────────────────────────────────────────────────
function StatsView({ apiBase }: { apiBase: string }) {
  const [stats, setStats] = useState<SessionStat[]>([]);
  const [totalLikes, setTotalLikes] = useState(0);
  const [totalDislikes, setTotalDislikes] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadStats = async () => {
    setIsLoading(true);
    try {
      const sessRes = await fetch(`${apiBase}/api/sessions`);
      const sessions: ApiSession[] = await sessRes.json();

      const results: SessionStat[] = await Promise.all(
        sessions.map(async (s) => {
          try {
            const msgRes = await fetch(`${apiBase}/api/sessions/${s.session_id}/messages`);
            const messages: ApiMessage[] = await msgRes.json();
            const likes = messages.filter(m => m.feedback === 'like').length;
            const dislikes = messages.filter(m => m.feedback === 'dislike').length;
            return { session: s, messages, likes, dislikes };
          } catch {
            return { session: s, messages: [], likes: 0, dislikes: 0 };
          }
        })
      );

      setStats(results);
      setTotalLikes(results.reduce((acc, r) => acc + r.likes, 0));
      setTotalDislikes(results.reduce((acc, r) => acc + r.dislikes, 0));
      setLoaded(true);
    } catch {}
    setIsLoading(false);
  };

  const feedbackMessages = (stat: SessionStat) =>
    stat.messages.filter(m => m.feedback && m.sender === 'bot');

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
      {!loaded && (
        <div className="flex flex-col items-center gap-3 py-8">
          <p className="text-[13px] text-gray-500 dark:text-gray-400">
            버튼을 눌러 전체 피드백 데이터를 불러오세요.
          </p>
          <button
            onClick={loadStats}
            disabled={isLoading}
            className="flex items-center gap-2 bg-[#004C97] hover:bg-[#003d80] text-white text-[13px] font-semibold px-5 py-2.5 rounded-xl transition disabled:opacity-60"
          >
            {isLoading
              ? <><Loader2 size={14} className="animate-spin" /> 불러오는 중...</>
              : <><BarChart2 size={14} /> 통계 불러오기</>
            }
          </button>
        </div>
      )}

      {loaded && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/50 px-4 py-3 text-center">
              <p className="text-[22px] font-bold text-gray-900 dark:text-white">{stats.length}</p>
              <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">총 대화</p>
            </div>
            <div className="rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/40 px-4 py-3 text-center">
              <p className="text-[22px] font-bold text-emerald-600 dark:text-emerald-400">{totalLikes}</p>
              <p className="text-[11px] text-emerald-500 dark:text-emerald-600 mt-0.5">👍 좋아요</p>
            </div>
            <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/40 px-4 py-3 text-center">
              <p className="text-[22px] font-bold text-red-500 dark:text-red-400">{totalDislikes}</p>
              <p className="text-[11px] text-red-400 dark:text-red-500 mt-0.5">👎 싫어요</p>
            </div>
          </div>

          <div>
            <p className="text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-2">
              세션별 피드백
            </p>
            <div className="flex flex-col gap-1.5">
              {stats.map((stat) => {
                const isExpanded = expandedId === stat.session.session_id;
                const feedbackMsgs = feedbackMessages(stat);
                return (
                  <div key={stat.session.session_id} className="rounded-xl border border-gray-100 dark:border-gray-700/50 overflow-hidden">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : stat.session.session_id)}
                      className="w-full flex items-center gap-2.5 px-3.5 py-2.5 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition text-left"
                    >
                      {isExpanded
                        ? <ChevronDown size={14} className="text-gray-400 shrink-0" />
                        : <ChevronRight size={14} className="text-gray-400 shrink-0" />
                      }
                      <p className="flex-1 text-[12px] font-medium text-gray-700 dark:text-gray-300 truncate">
                        {stat.session.title ?? '제목 없음'}
                      </p>
                      <span className="text-[10px] text-gray-400 dark:text-gray-500 shrink-0 mr-1">
                        {new Date(stat.session.updated_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
                      </span>
                      {stat.likes > 0 && (
                        <span className="flex items-center gap-0.5 text-[11px] text-emerald-500 font-semibold shrink-0">
                          <ThumbsUp size={10} /> {stat.likes}
                        </span>
                      )}
                      {stat.dislikes > 0 && (
                        <span className="flex items-center gap-0.5 text-[11px] text-red-400 font-semibold shrink-0 ml-1">
                          <ThumbsDown size={10} /> {stat.dislikes}
                        </span>
                      )}
                      {stat.likes === 0 && stat.dislikes === 0 && (
                        <span className="text-[10px] text-gray-300 dark:text-gray-600 shrink-0">없음</span>
                      )}
                    </button>

                    {isExpanded && (
                      <div className="px-3.5 py-2.5 flex flex-col gap-2 border-t border-gray-100 dark:border-gray-700/40 bg-white dark:bg-[#111827]">
                        {feedbackMsgs.length === 0 ? (
                          <p className="text-[12px] text-gray-400 dark:text-gray-500 py-1">피드백이 남겨진 답변이 없습니다.</p>
                        ) : (
                          feedbackMsgs.map((m) => (
                            <div key={m.message_id} className="flex items-start gap-2.5">
                              <span className={`mt-0.5 shrink-0 ${m.feedback === 'like' ? 'text-emerald-500' : 'text-red-400'}`}>
                                {m.feedback === 'like' ? <ThumbsUp size={12} /> : <ThumbsDown size={12} />}
                              </span>
                              <p className="text-[12px] text-gray-600 dark:text-gray-400 leading-relaxed line-clamp-2">
                                {m.content.slice(0, 120)}{m.content.length > 120 ? '...' : ''}
                              </p>
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── 모달 래퍼 ──────────────────────────────────────────────────────────────────
export default function FeedbackAdminModal({ apiBase, onClose }: Props) {
  const [authenticated, setAuthenticated] = useState(() => {
    if (typeof window === 'undefined') return false;
    return sessionStorage.getItem('admin_auth') === 'true';
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-white dark:bg-[#111827] rounded-2xl shadow-2xl flex flex-col max-h-[80vh] overflow-hidden">

        {/* 모달 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700/60 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#004C97] flex items-center justify-center">
              <BarChart2 size={16} className="text-white" />
            </div>
            <div>
              <p className="text-[14px] font-bold text-gray-900 dark:text-white">피드백 현황</p>
              <p className="text-[11px] text-gray-400 dark:text-gray-500">관리자 전용</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* 인증 전: 비밀번호 입력 / 인증 후: 통계 */}
        {authenticated
          ? <StatsView apiBase={apiBase} />
          : <PasswordGate onSuccess={() => setAuthenticated(true)} />
        }
      </div>
    </div>
  );
}
