export type FontSize = 'normal' | 'large' | 'largest';
export type Feedback = 'like' | 'dislike' | null;

export type Message = {
  id: string;
  messageId?: number;     // 백엔드 DB ID (피드백 API 호출용)
  role: 'user' | 'bot';
  content: string;
  time: string;
  isStreaming?: boolean;
  feedback?: Feedback;
};

export type StoredConversation = {
  id: string;             // session_id
  title: string;
  date: string;
  messages: Message[];
};

// 백엔드 API 응답 타입
export type ApiSession = {
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type ApiMessage = {
  message_id: number;
  session_id: string;
  sender: 'user' | 'bot';
  content: string;
  metadata_json: string | null;
  feedback: 'like' | 'dislike' | null;
  created_at: string;
};
