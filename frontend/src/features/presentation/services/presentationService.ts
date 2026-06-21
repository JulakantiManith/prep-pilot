import apiClient from "@/shared/lib/axios";

// --- Request Types ---

export interface CreatePresentationSessionRequest {
  title?: string;
  topic?: string;
  duration_estimate_minutes?: number;
}

// --- Response Types ---

export interface PresentationSession {
  id: string;
  user_id: string;
  session_type: string;
  title: string | null;
  topic: string | null;
  overall_score: number | null;
  confidence_score: number | null;
  communication_score: number | null;
  duration_seconds: number | null;
  status: string;
  recording_url: string | null;
  materials_url: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface CreatePresentationSessionResponse {
  session: PresentationSession;
}

export interface UploadRecordingResponse {
  session_id: string;
  recording_url: string;
  message: string;
}

export interface UploadMaterialsResponse {
  session_id: string;
  materials_url: string;
  message: string;
}

export interface PresentationScoresResponse {
  speaking_speed: number;
  clarity: number;
  structure: number;
  communication: number;
  engagement: number;
}

export interface PresentationFeedbackResponse {
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  presentation_scores: PresentationScoresResponse | null;
}

export interface CompletePresentationResponse {
  session: PresentationSession;
  scores: PresentationScoresResponse | null;
  feedback: PresentationFeedbackResponse | null;
}

export interface SubmitPresentationResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface PresentationStatusResponse {
  session_id: string;
  status: string;
  session: PresentationSession;
  scores?: PresentationScoresResponse | null;
  feedback?: PresentationFeedbackResponse | null;
}

// --- API Functions ---

export async function createPresentationSession(
  data: CreatePresentationSessionRequest
): Promise<CreatePresentationSessionResponse> {
  const response = await apiClient.post<CreatePresentationSessionResponse>(
    "/sessions/presentation",
    data
  );
  return response.data;
}

export async function uploadRecording(
  sessionId: string,
  recordingBlob: Blob,
  filename: string = "recording.webm"
): Promise<UploadRecordingResponse> {
  const formData = new FormData();
  formData.append("recording", recordingBlob, filename);

  const response = await apiClient.post<UploadRecordingResponse>(
    `/sessions/presentation/${sessionId}/recording`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
}

export async function uploadMaterials(
  sessionId: string,
  file: File
): Promise<UploadMaterialsResponse> {
  const formData = new FormData();
  formData.append("materials", file, file.name);

  const response = await apiClient.post<UploadMaterialsResponse>(
    `/sessions/presentation/${sessionId}/materials`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
}

/**
 * Submit presentation for background analysis.
 * Returns immediately with status "processing".
 */
export async function completePresentationSession(
  sessionId: string
): Promise<SubmitPresentationResponse> {
  const response = await apiClient.post<SubmitPresentationResponse>(
    `/sessions/presentation/${sessionId}/complete`
  );
  return response.data;
}

/**
 * Poll the processing status of a presentation session.
 * Returns full results when status is "completed".
 */
export async function getPresentationStatus(
  sessionId: string
): Promise<PresentationStatusResponse> {
  const response = await apiClient.get<PresentationStatusResponse>(
    `/sessions/presentation/${sessionId}/status`
  );
  return response.data;
}
