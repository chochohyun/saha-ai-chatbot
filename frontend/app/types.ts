export type FontSize = 'normal' | 'large' | 'largest';
export type Feedback = 'good' | 'bad' | null;

export type Message = {
  id: string;
  role: 'user' | 'bot';
  content: string;
  time: string;
  isStreaming?: boolean;
  feedback?: Feedback;
};

export type StoredConversation = {
  id: string;
  title: string;
  date: string;
  messages: Message[];
};
