import apiClient from "@/shared/lib/axios";

// API response types (snake_case from backend)
interface ProfileApiResponse {
  id: string | null;
  user_id: string;
  target_role: string | null;
  experience_level: string | null;
  skills: string[] | null;
  theme_preference: string | null;
  updated_at: string | null;
}

interface ResumeUploadApiResponse {
  id: string;
  user_id: string;
  file_path: string;
  file_name: string;
  file_size: number;
  extraction_status: string;
  uploaded_at: string;
}

interface ResumeMetadataApiResponse {
  id: string;
  user_id: string;
  file_path: string;
  file_name: string;
  file_size: number;
  extracted_data: Record<string, unknown> | null;
  extraction_confidence: number | null;
  user_confirmed: boolean | null;
  extraction_status: string;
  uploaded_at: string;
}

// Frontend types (camelCase)
export interface ProfileData {
  id: string | null;
  userId: string;
  targetRole: string | null;
  experienceLevel: string | null;
  skills: string[];
  themePreference: string | null;
  updatedAt: string | null;
}

export interface ProfileUpdateData {
  targetRole?: string;
  experienceLevel?: string;
  skills?: string[];
}

export interface ResumeUploadData {
  id: string;
  userId: string;
  filePath: string;
  fileName: string;
  fileSize: number;
  extractionStatus: string;
  uploadedAt: string;
}

export interface ResumeMetadata {
  id: string;
  userId: string;
  filePath: string;
  fileName: string;
  fileSize: number;
  extractedData: Record<string, unknown> | null;
  extractionConfidence: number | null;
  userConfirmed: boolean | null;
  extractionStatus: string;
  uploadedAt: string;
}

function mapProfileResponse(data: ProfileApiResponse): ProfileData {
  return {
    id: data.id,
    userId: data.user_id,
    targetRole: data.target_role,
    experienceLevel: data.experience_level,
    skills: data.skills ?? [],
    themePreference: data.theme_preference,
    updatedAt: data.updated_at,
  };
}

function mapResumeUploadResponse(data: ResumeUploadApiResponse): ResumeUploadData {
  return {
    id: data.id,
    userId: data.user_id,
    filePath: data.file_path,
    fileName: data.file_name,
    fileSize: data.file_size,
    extractionStatus: data.extraction_status,
    uploadedAt: data.uploaded_at,
  };
}

function mapResumeMetadataResponse(data: ResumeMetadataApiResponse): ResumeMetadata {
  return {
    id: data.id,
    userId: data.user_id,
    filePath: data.file_path,
    fileName: data.file_name,
    fileSize: data.file_size,
    extractedData: data.extracted_data,
    extractionConfidence: data.extraction_confidence,
    userConfirmed: data.user_confirmed,
    extractionStatus: data.extraction_status,
    uploadedAt: data.uploaded_at,
  };
}

export async function getProfile(): Promise<ProfileData> {
  const response = await apiClient.get<ProfileApiResponse>("/profile");
  return mapProfileResponse(response.data);
}

export async function updateProfile(data: ProfileUpdateData): Promise<ProfileData> {
  const payload: Record<string, unknown> = {};
  if (data.targetRole !== undefined) payload.target_role = data.targetRole;
  if (data.experienceLevel !== undefined) payload.experience_level = data.experienceLevel;
  if (data.skills !== undefined) payload.skills = data.skills;

  const response = await apiClient.put<ProfileApiResponse>("/profile", payload);
  return mapProfileResponse(response.data);
}

export async function uploadResume(
  file: File,
  onProgress?: (percent: number) => void
): Promise<ResumeUploadData> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<ResumeUploadApiResponse>(
    "/profile/resume",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    }
  );
  return mapResumeUploadResponse(response.data);
}

export async function getResumeMetadata(): Promise<ResumeMetadata | null> {
  try {
    const response = await apiClient.get<ResumeMetadataApiResponse>("/profile/resume");
    return mapResumeMetadataResponse(response.data);
  } catch (error: unknown) {
    // 404 means no resume uploaded yet — not an error
    if (
      error &&
      typeof error === "object" &&
      "response" in error &&
      (error as { response?: { status?: number } }).response?.status === 404
    ) {
      return null;
    }
    throw error;
  }
}
