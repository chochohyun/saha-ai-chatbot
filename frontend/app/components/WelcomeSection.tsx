'use client';

const PROMPT_CARDS = [
  {
    icon: '🚗',
    title: '불법 주정차 신고',
    desc: '단속 방법 및 신고 절차 안내',
    q: '불법 주정차 단속 및 신고 방법을 알려주세요',
  },
  {
    icon: '📄',
    title: '주민등록 전출입',
    desc: '전입·전출 신고 절차 및 서류',
    q: '주민등록 전출입 신고 방법을 알려주세요',
  },
  {
    icon: '👶',
    title: '출산·영유아 혜택',
    desc: '출산 지원금 및 육아 복지 안내',
    q: '출산 지원금 및 영유아 혜택이 뭐가 있나요?',
  },
  {
    icon: '🗑️',
    title: '대형 폐기물 배출',
    desc: '스티커 구매 및 배출 방법',
    q: '대형 폐기물 배출 스티커 안내해주세요',
  },
  {
    icon: '🏥',
    title: '보건소 서비스',
    desc: '건강검진·예방접종 등 안내',
    q: '보건소에서 받을 수 있는 서비스가 뭐가 있나요?',
  },
  {
    icon: '📘',
    title: '여권 발급',
    desc: '여권 신청 절차 및 준비 서류',
    q: '여권 처음 만들려면 뭐가 필요한가요?',
  },
];

type Props = {
  onSend: (text: string) => void;
  isLoading: boolean;
};

export default function WelcomeSection({ onSend, isLoading }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-8 px-4 py-8 text-center">

      {/* 마스코트 + 인사말 */}
      <div className="flex flex-col items-center gap-4">
        <div className="w-24 h-24 lg:w-32 lg:h-32">
          <img src="/saharu.png" alt="사하루" className="w-full h-full object-contain" />
        </div>
        <div className="flex flex-col gap-1.5">
          <h2 className="text-[18px] lg:text-[20px] font-bold text-gray-800 dark:text-gray-100">
            안녕하세요! 저는 사하루입니다 😊
          </h2>
          <p className="text-[13px] text-gray-500 dark:text-gray-400 leading-relaxed">
            사하구청 민원 정보를 빠르게 안내해드립니다.<br className="hidden sm:block" />
            아래 카드를 선택하거나 직접 질문을 입력해보세요.
          </p>
        </div>
      </div>

      {/* 추천 질문 카드 그리드 */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 w-full max-w-2xl">
        {PROMPT_CARDS.map((card) => (
          <button
            key={card.title}
            onClick={() => onSend(card.q)}
            disabled={isLoading}
            className="flex flex-col items-start gap-2.5 text-left bg-white dark:bg-[#1c2333] border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-4 shadow-sm hover:shadow-md hover:-translate-y-0.5 hover:border-[#004C97] dark:hover:border-blue-500 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
          >
            <span className="text-[24px]">{card.icon}</span>
            <div>
              <p className="text-[13px] font-bold text-gray-800 dark:text-gray-100 leading-tight">{card.title}</p>
              <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-1 leading-relaxed">{card.desc}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
