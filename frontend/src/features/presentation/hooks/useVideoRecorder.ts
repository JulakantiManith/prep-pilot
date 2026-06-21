import { useState, useRef, useCallback, useEffect } from "react";

export type VideoRecorderStatus =
  | "idle"
  | "requesting"
  | "recording"
  | "stopped"
  | "error";

// Maximum recording duration in seconds (20 minutes)
const MAX_RECORDING_DURATION_SECONDS = 20 * 60;

interface VideoRecorderState {
  status: VideoRecorderStatus;
  videoBlob: Blob | null;
  error: string | null;
  duration: number;
  previewUrl: string | null;
}

export function useVideoRecorder() {
  const [state, setState] = useState<VideoRecorderState>({
    status: "idle",
    videoBlob: null,
    error: null,
    duration: 0,
    previewUrl: null,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const getVideoMimeType = (): string => {
    if (MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")) {
      return "video/webm;codecs=vp9,opus";
    }
    if (MediaRecorder.isTypeSupported("video/webm;codecs=vp8,opus")) {
      return "video/webm;codecs=vp8,opus";
    }
    if (MediaRecorder.isTypeSupported("video/webm")) {
      return "video/webm";
    }
    if (MediaRecorder.isTypeSupported("video/mp4")) {
      return "video/mp4";
    }
    return "";
  };

  const startRecording = useCallback(async () => {
    setState((prev) => ({
      ...prev,
      status: "requesting",
      error: null,
      videoBlob: null,
      previewUrl: null,
    }));
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });
      streamRef.current = stream;

      const mimeType = getVideoMimeType();
      const options: MediaRecorderOptions = {};
      if (mimeType) {
        options.mimeType = mimeType;
      }

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mimeType || "video/webm",
        });
        const url = URL.createObjectURL(blob);

        setState((prev) => ({
          ...prev,
          status: "stopped",
          videoBlob: blob,
          previewUrl: url,
        }));

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        // Clear timer
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      };

      mediaRecorder.onerror = () => {
        setState((prev) => ({
          ...prev,
          status: "error",
          error: "Recording failed. Please try again.",
        }));
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      };

      mediaRecorder.start();
      startTimeRef.current = Date.now();

      // Update duration every second and auto-stop at max duration
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setState((prev) => ({
          ...prev,
          duration: elapsed,
        }));
        // Auto-stop at maximum duration (20 minutes)
        if (elapsed >= MAX_RECORDING_DURATION_SECONDS) {
          if (
            mediaRecorderRef.current &&
            mediaRecorderRef.current.state === "recording"
          ) {
            mediaRecorderRef.current.stop();
          }
        }
      }, 1000);

      setState((prev) => ({ ...prev, status: "recording", duration: 0 }));
    } catch (err: unknown) {
      let errorMessage = "Could not access camera and microphone.";

      if (err instanceof DOMException) {
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          errorMessage =
            "Camera and microphone access was denied. Please allow access in your browser settings and try again.";
        } else if (err.name === "NotFoundError") {
          errorMessage =
            "No camera found. Please connect a camera and try again.";
        } else if (err.name === "NotReadableError") {
          errorMessage =
            "Camera or microphone is already in use by another application. Please close other apps and try again.";
        }
      }

      setState((prev) => ({
        ...prev,
        status: "error",
        error: errorMessage,
      }));
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const getStream = useCallback(() => {
    return streamRef.current;
  }, []);

  const resetRecorder = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    // Revoke previous preview URL
    if (state.previewUrl) {
      URL.revokeObjectURL(state.previewUrl);
    }
    chunksRef.current = [];
    setState({
      status: "idle",
      videoBlob: null,
      error: null,
      duration: 0,
      previewUrl: null,
    });
  }, [state.previewUrl]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  return {
    ...state,
    startRecording,
    stopRecording,
    resetRecorder,
    getStream,
  };
}
