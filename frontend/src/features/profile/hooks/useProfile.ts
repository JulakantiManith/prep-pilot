import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as profileService from "../services/profileService";
import type { ProfileUpdateData } from "../services/profileService";

const PROFILE_QUERY_KEY = ["profile"] as const;
const RESUME_QUERY_KEY = ["profile", "resume"] as const;

export function useProfile() {
  return useQuery({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: profileService.getProfile,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProfileUpdateData) => profileService.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY });
    },
  });
}

export function useUploadResume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (percent: number) => void }) =>
      profileService.uploadResume(file, onProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RESUME_QUERY_KEY });
    },
  });
}

export function useResumeMetadata() {
  return useQuery({
    queryKey: RESUME_QUERY_KEY,
    queryFn: profileService.getResumeMetadata,
    retry: false,
  });
}
