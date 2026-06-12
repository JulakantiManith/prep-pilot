import axios from "axios";
import { supabase } from "./supabase";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL as string || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: attach auth token
apiClient.interceptors.request.use(
  async (config) => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      // Only retry once to avoid infinite loops
      const originalRequest = error.config;
      if (!originalRequest || (originalRequest as Record<string, unknown>)._retry) {
        return Promise.reject(error);
      }
      (originalRequest as Record<string, unknown>)._retry = true;

      // Attempt token refresh
      const { error: refreshError } = await supabase.auth.refreshSession();

      if (refreshError) {
        // Refresh failed — sign out and let the auth context handle redirect
        await supabase.auth.signOut();
        return Promise.reject(error);
      }

      // Retry the original request with new token
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;

      if (token && originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${token}`;
      }

      return apiClient(originalRequest);
    }

    return Promise.reject(error);
  }
);

export default apiClient;
