import apiClient from "@/shared/lib/axios";

// API response types (snake_case from backend)
interface OverviewApiData {
  total_interview_sessions: number;
  total_presentation_sessions: number;
  average_overall_score: number | null;
  latest_confidence_score: number | null;
  latest_communication_score: number | null;
}

interface WeeklyProgressApiData {
  date: string;
  average_score: number;
  session_count: number;
}

interface RecentSessionApiData {
  session_type: string;
  created_at: string;
  overall_score: number | null;
}

interface AnalyticsOverviewApiResponse {
  has_sessions: boolean;
  overview: OverviewApiData;
  weekly_progress: WeeklyProgressApiData[];
  recent_sessions: RecentSessionApiData[];
}

// Frontend types (camelCase)
export interface DashboardOverview {
  totalInterviewSessions: number;
  totalPresentationSessions: number;
  averageOverallScore: number | null;
  latestConfidenceScore: number | null;
  latestCommunicationScore: number | null;
}

export interface WeeklyProgress {
  date: string;
  averageScore: number;
  sessionCount: number;
}

export interface RecentSession {
  sessionType: string;
  createdAt: string;
  overallScore: number | null;
}

export interface DashboardData {
  hasSessions: boolean;
  overview: DashboardOverview;
  weeklyProgress: WeeklyProgress[];
  recentSessions: RecentSession[];
}

// Mapper functions
function mapOverview(data: OverviewApiData): DashboardOverview {
  return {
    totalInterviewSessions: data.total_interview_sessions,
    totalPresentationSessions: data.total_presentation_sessions,
    averageOverallScore: data.average_overall_score,
    latestConfidenceScore: data.latest_confidence_score,
    latestCommunicationScore: data.latest_communication_score,
  };
}

function mapWeeklyProgress(data: WeeklyProgressApiData[]): WeeklyProgress[] {
  return data.map((item) => ({
    date: item.date,
    averageScore: item.average_score,
    sessionCount: item.session_count,
  }));
}

function mapRecentSessions(data: RecentSessionApiData[]): RecentSession[] {
  return data.map((item) => ({
    sessionType: item.session_type,
    createdAt: item.created_at,
    overallScore: item.overall_score,
  }));
}

function mapDashboardResponse(data: AnalyticsOverviewApiResponse): DashboardData {
  return {
    hasSessions: data.has_sessions,
    overview: mapOverview(data.overview),
    weeklyProgress: mapWeeklyProgress(data.weekly_progress),
    recentSessions: mapRecentSessions(data.recent_sessions),
  };
}

export type TimeRange = "daily" | "weekly" | "monthly" | "3months" | "yearly";

export async function getDashboardData(timeRange: TimeRange = "weekly"): Promise<DashboardData> {
  const response = await apiClient.get<AnalyticsOverviewApiResponse>(
    "/analytics/overview",
    { params: { time_range: timeRange } }
  );
  return mapDashboardResponse(response.data);
}
