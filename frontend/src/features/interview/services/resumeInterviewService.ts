import apiClient from "@/shared/lib/axios";

// Types matching backend schemas

export interface ExtractedProject {
  name: string;
  description: string;
  technologies: string;
}

export interface ExtractedExperience {
  title: string;
  company: string;
  duration: string;
  description: string;
}

export interface ExtractedEducation {
  degree: string;
  institution: string;
  year: string;
}

export interface ExtractedResumeData {
  skills: string[];
  projects: ExtractedProject[];
  experience: ExtractedExperience[];
  education: ExtractedEducation[];
}

export interface ResumeParseResponse {
  id: string;
  extraction_status: "completed" | "failed";
  extracted_data: ExtractedResumeData | null;
  extraction_confidence: number | null;
  message: string | null;
}

export interface ResumeExtractedResponse {
  id: string;
  user_id: string;
  file_name: string;
  extracted_data: ExtractedResumeData | null;
  extraction_confidence: number | null;
  extraction_status: string;
  user_confirmed: boolean;
}

export interface ResumeEditRequest {
  skills?: string[];
  projects?: ExtractedProject[];
  experience?: ExtractedExperience[];
  education?: ExtractedEducation[];
}

export interface ResumeConfirmResponse {
  id: string;
  user_confirmed: boolean;
  message: string;
}

export async function parseResume(resumeId: string): Promise<ResumeParseResponse> {
  const response = await apiClient.post<ResumeParseResponse>(
    "/resume/parse",
    null,
    { params: { resume_id: resumeId } }
  );
  return response.data;
}

export async function getExtractedData(resumeId: string): Promise<ResumeExtractedResponse> {
  const response = await apiClient.get<ResumeExtractedResponse>(
    `/resume/extracted/${resumeId}`
  );
  return response.data;
}

export async function editExtractedData(
  resumeId: string,
  data: ResumeEditRequest
): Promise<ResumeExtractedResponse> {
  const response = await apiClient.put<ResumeExtractedResponse>(
    `/resume/extracted/${resumeId}`,
    data
  );
  return response.data;
}

export async function confirmExtractedData(
  resumeId: string
): Promise<ResumeConfirmResponse> {
  const response = await apiClient.post<ResumeConfirmResponse>(
    `/resume/confirm/${resumeId}`
  );
  return response.data;
}
