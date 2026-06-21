import apiClient from "@/shared/lib/axios";

// API response types (snake_case from backend)
interface SessionListItemApi {
  id: string;
  session_type: string;
  created_at: string;
  duration_seconds: number | null;
  overall_score: number | null;
  status: string;
}

interface SessionHistoryListApiResponse {
  sessions: SessionListItemApi[];
  total_count: number;
  total_pages: number;
  page: number;
  page_size: number;
}

interface AnswerDetailApi {
  question_index: number;
  question_text: string | null;
  transcript: string | null;
  wpm: number | null;
  total_words: number | null;
  filler_word_count: number | null;
  filler_words_detail: unknown;
  speaking_duration: number | null;
  avg_pause_duration: number | null;
  communication_score: number | null;
  confidence_score: number | null;
  ai_evaluation: unknown;
  created_at: string | null;
}

interface SessionFeedbackDetailApi {
  strengths: string[] | null;
  weaknesses: string[] | null;
  recommendations: string[] | null;
  technical_evaluation: unknown;
  presentation_scores: unknown;
}

interface SessionDetailApiResponse {
  id: string;
  session_type: string;
  interview_type: string | null;
  role: string | null;
  topic: string | null;
  difficulty: string | null;
  overall_score: number | null;
  confidence_score: number | null;
  communication_score: number | null;
  duration_seconds: number | null;
  status: string | null;
  created_at: string;
  completed_at: string | null;
  answers: AnswerDetailApi[];
  feedback: SessionFeedbackDetailApi | null;
}

// Frontend types (camelCase)
export interface SessionListItem {
  id: string;
  sessionType: string;
  createdAt: string;
  durationSeconds: number | null;
  overallScore: number | null;
  status: string;
}

export interface SessionHistoryList {
  sessions: SessionListItem[];
  totalCount: number;
  totalPages: number;
  page: number;
  pageSize: number;
}

export interface AnswerDetail {
  questionIndex: number;
  questionText: string | null;
  transcript: string | null;
  wpm: number | null;
  totalWords: number | null;
  fillerWordCount: number | null;
  fillerWordsDetail: unknown;
  speakingDuration: number | null;
  avgPauseDuration: number | null;
  communicationScore: number | null;
  confidenceScore: number | null;
  aiEvaluation: unknown;
  createdAt: string | null;
}

export interface SessionFeedbackDetail {
  strengths: string[] | null;
  weaknesses: string[] | null;
  recommendations: string[] | null;
  technicalEvaluation: unknown;
  presentationScores: unknown;
}

export interface SessionDetail {
  id: string;
  sessionType: string;
  interviewType: string | null;
  role: string | null;
  topic: string | null;
  difficulty: string | null;
  overallScore: number | null;
  confidenceScore: number | null;
  communicationScore: number | null;
  durationSeconds: number | null;
  status: string | null;
  createdAt: string;
  completedAt: string | null;
  answers: AnswerDetail[];
  feedback: SessionFeedbackDetail | null;
}

export interface HistoryFilters {
  sessionType?: string;
  startDate?: string;
  endDate?: string;
}

// Mapper functions
function mapSessionListItem(item: SessionListItemApi): SessionListItem {
  return {
    id: item.id,
    sessionType: item.session_type,
    createdAt: item.created_at,
    durationSeconds: item.duration_seconds,
    overallScore: item.overall_score,
    status: item.status || "completed",
  };
}

function mapSessionHistoryList(data: SessionHistoryListApiResponse): SessionHistoryList {
  return {
    sessions: data.sessions.map(mapSessionListItem),
    totalCount: data.total_count,
    totalPages: data.total_pages,
    page: data.page,
    pageSize: data.page_size,
  };
}

function mapAnswerDetail(answer: AnswerDetailApi): AnswerDetail {
  return {
    questionIndex: answer.question_index,
    questionText: answer.question_text,
    transcript: answer.transcript,
    wpm: answer.wpm,
    totalWords: answer.total_words,
    fillerWordCount: answer.filler_word_count,
    fillerWordsDetail: answer.filler_words_detail,
    speakingDuration: answer.speaking_duration,
    avgPauseDuration: answer.avg_pause_duration,
    communicationScore: answer.communication_score,
    confidenceScore: answer.confidence_score,
    aiEvaluation: answer.ai_evaluation,
    createdAt: answer.created_at,
  };
}

function mapSessionDetail(data: SessionDetailApiResponse): SessionDetail {
  return {
    id: data.id,
    sessionType: data.session_type,
    interviewType: data.interview_type,
    role: data.role,
    topic: data.topic,
    difficulty: data.difficulty,
    overallScore: data.overall_score,
    confidenceScore: data.confidence_score,
    communicationScore: data.communication_score,
    durationSeconds: data.duration_seconds,
    status: data.status,
    createdAt: data.created_at,
    completedAt: data.completed_at,
    answers: data.answers.map(mapAnswerDetail),
    feedback: data.feedback
      ? {
          strengths: data.feedback.strengths,
          weaknesses: data.feedback.weaknesses,
          recommendations: data.feedback.recommendations,
          technicalEvaluation: data.feedback.technical_evaluation,
          presentationScores: data.feedback.presentation_scores,
        }
      : null,
  };
}

// API functions
export async function getSessionHistory(
  page: number = 1,
  filters?: HistoryFilters
): Promise<SessionHistoryList> {
  const params: Record<string, string | number> = { page };

  if (filters?.sessionType) {
    params.session_type = filters.sessionType;
  }
  if (filters?.startDate) {
    params.start_date = filters.startDate;
  }
  if (filters?.endDate) {
    params.end_date = filters.endDate;
  }

  const response = await apiClient.get<SessionHistoryListApiResponse>("/history", {
    params,
  });
  return mapSessionHistoryList(response.data);
}

export async function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  const response = await apiClient.get<SessionDetailApiResponse>(
    `/history/${sessionId}`
  );
  return mapSessionDetail(response.data);
}
