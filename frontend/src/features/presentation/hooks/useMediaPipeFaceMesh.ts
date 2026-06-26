import { useRef, useCallback, useEffect, useState } from "react";
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";

// --- Landmark Indices ---
// Iris landmarks (available with refineLandmarks: true)
const LEFT_IRIS_CENTER = 468;
const RIGHT_IRIS_CENTER = 473;

// Eye corner landmarks
const LEFT_EYE_INNER = 133;
const LEFT_EYE_OUTER = 33;
const RIGHT_EYE_INNER = 362;
const RIGHT_EYE_OUTER = 263;

// Head pose estimation landmarks
const NOSE_TIP = 1;
const CHIN = 199;
const LEFT_EYE_LEFT_CORNER = 33;
const RIGHT_EYE_RIGHT_CORNER = 263;
const FOREHEAD = 10;

// Face oval for bounding box estimation
const FACE_OVAL_TOP = 10;
const FACE_OVAL_BOTTOM = 152;
const FACE_OVAL_LEFT = 234;
const FACE_OVAL_RIGHT = 454;

// --- Types ---
export type FaceStatus = "facing-camera" | "turned-away" | "not-detected" | "loading";

export interface HeadPose {
  pitch: number; // vertical rotation (nodding)
  yaw: number;   // horizontal rotation (shaking head)
  roll: number;  // tilting
}

export interface FacePosition {
  tooFar: boolean;
  tooClose: boolean;
  outOfFrame: boolean;
  centered: boolean;
}

export interface FrameMetrics {
  faceStatus: FaceStatus;
  eyeContact: boolean; // looking at camera this frame
  headPose: HeadPose | null;
  facePosition: FacePosition | null;
  brightness: number; // 0-255 average
}

export interface SessionMetrics {
  totalFrames: number;
  faceDetectedFrames: number;
  faceVisibilityPercentage: number;
  eyeContactFrames: number;
  eyeContactPercentage: number;
  faceCenteredPercentage: number;
  blinkCount: number;
  blinksPerMinute: number;
  headPoseHistory: HeadPose[];
  avgPitch: number;
  avgYaw: number;
  avgRoll: number;
  stdPitch: number;
  stdYaw: number;
  stdRoll: number;
  headStability: "stable" | "excessive";
  presentationPresenceScore: number; // 0-100 composite score
  warnings: string[];
}

interface MediaPipeFaceMeshOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  isActive: boolean;
  showMesh?: boolean; // draw face mesh overlay (default true)
}

const GAZE_THRESHOLD = 0.08; // max iris displacement — strict but stable
const HEAD_YAW_THRESHOLD = 15; // degrees — moderate turn triggers "turned away"
const HEAD_PITCH_THRESHOLD = 5; // degrees — very strict: minimal head nod allowed
const HEAD_ROLL_THRESHOLD = 12; // degrees — head tilt threshold
const STABILITY_THRESHOLD = 4.0; // std dev degrees for "excessive"
const FACE_SIZE_MIN = 0.08; // face too far if occupies < 8% of frame
const FACE_SIZE_MAX = 0.65; // face too close if occupies > 65% of frame

// Blink and temporal smoothing constants
const BLINK_EAR_THRESHOLD = 0.18; // Eye Aspect Ratio below this = eyes closed
const BLINK_MAX_DURATION_MS = 500; // up to 500ms eye closure = blink (not looking away)
const GAZE_LOSS_MIN_DURATION_MS = 200; // must look away for 200ms+ to count as loss (fast response)

/**
 * Core hook for MediaPipe Face Mesh processing.
 * Runs entirely client-side in the browser using WASM + WebGL.
 *
 * Provides:
 * - Real-time face detection with 478 landmarks
 * - Eye contact tracking via iris position
 * - Head pose estimation (pitch, yaw, roll)
 * - Face positioning feedback
 * - Lighting quality detection
 * - Accumulated session metrics for the final report
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
 */
export function useMediaPipeFaceMesh({
  videoRef,
  canvasRef,
  isActive,
  showMesh = true,
}: MediaPipeFaceMeshOptions) {
  const [faceStatus, setFaceStatus] = useState<FaceStatus>("loading");
  const [isReady, setIsReady] = useState(false);
  const [currentWarnings, setCurrentWarnings] = useState<string[]>([]);

  const faceLandmarkerRef = useRef<FaceLandmarker | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const isActiveRef = useRef(isActive);
  const lastFrameTimeRef = useRef(0);

  // Session metrics accumulation
  const metricsRef = useRef<{
    totalFrames: number;
    faceDetectedFrames: number;
    eyeContactFrames: number;
    faceCenteredFrames: number;
    blinkCount: number;
    headPoses: HeadPose[];
    warnings: Set<string>;
  }>({
    totalFrames: 0,
    faceDetectedFrames: 0,
    eyeContactFrames: 0,
    faceCenteredFrames: 0,
    blinkCount: 0,
    headPoses: [],
    warnings: new Set(),
  });

  // Temporal gaze state for blink/smoothing logic
  const gazeStateRef = useRef<{
    lastEyeContactRaw: boolean;
    eyeContactSmoothed: boolean;
    gazeLostTimestamp: number | null;
    blinkStartTimestamp: number | null;
    isBlinking: boolean;
    lastBlinkCounted: boolean; // prevent double-counting a single blink
  }>({
    lastEyeContactRaw: true,
    eyeContactSmoothed: true,
    gazeLostTimestamp: null,
    blinkStartTimestamp: null,
    isBlinking: false,
    lastBlinkCounted: false,
  });

  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  // Initialize MediaPipe FaceLandmarker
  useEffect(() => {
    if (!isActive) return;

    let cancelled = false;

    const init = async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );

        if (cancelled) return;

        const landmarker = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
            delegate: "GPU",
          },
          runningMode: "VIDEO",
          numFaces: 1,
          outputFaceBlendshapes: false,
          outputFacialTransformationMatrixes: true,
        });

        if (cancelled) return;

        faceLandmarkerRef.current = landmarker;
        setIsReady(true);
        setFaceStatus("not-detected");
        console.debug("[MediaPipe] FaceLandmarker initialized");
      } catch (err) {
        console.error("[MediaPipe] Failed to initialize:", err);
        setFaceStatus("not-detected");
      }
    };

    init();

    return () => {
      cancelled = true;
      if (faceLandmarkerRef.current) {
        faceLandmarkerRef.current.close();
        faceLandmarkerRef.current = null;
      }
      setIsReady(false);
    };
  }, [isActive]);

  // Compute Eye Aspect Ratio (EAR) to detect blinks
  const computeEAR = useCallback(
    (lm: { x: number; y: number; z: number }[]): number => {
      const leftV1 = Math.abs(lm[159]!.y - lm[145]!.y);
      const leftV2 = Math.abs(lm[158]!.y - lm[153]!.y);
      const leftH = Math.abs(lm[LEFT_EYE_OUTER]!.x - lm[LEFT_EYE_INNER]!.x);
      const leftEAR = leftH > 0.001 ? (leftV1 + leftV2) / (2 * leftH) : 0;

      const rightV1 = Math.abs(lm[386]!.y - lm[374]!.y);
      const rightV2 = Math.abs(lm[385]!.y - lm[380]!.y);
      const rightH = Math.abs(lm[RIGHT_EYE_OUTER]!.x - lm[RIGHT_EYE_INNER]!.x);
      const rightEAR = rightH > 0.001 ? (rightV1 + rightV2) / (2 * rightH) : 0;

      return (leftEAR + rightEAR) / 2;
    },
    []
  );

  // Raw iris displacement check (no smoothing)
  const computeRawGaze = useCallback(
    (lm: { x: number; y: number; z: number }[]): boolean => {
      // Left eye
      const leftEyeW = Math.abs(lm[LEFT_EYE_OUTER]!.x - lm[LEFT_EYE_INNER]!.x);
      if (leftEyeW < 0.001) return false;
      const leftCX = (lm[LEFT_EYE_INNER]!.x + lm[LEFT_EYE_OUTER]!.x) / 2;
      const leftDX = Math.abs(lm[LEFT_IRIS_CENTER]!.x - leftCX) / leftEyeW;
      const leftEyeH = Math.abs(lm[145]!.y - lm[159]!.y);
      const leftCY = (lm[159]!.y + lm[145]!.y) / 2;
      const leftDY = leftEyeH > 0.001 ? Math.abs(lm[LEFT_IRIS_CENTER]!.y - leftCY) / leftEyeH : 0;

      // Right eye
      const rightEyeW = Math.abs(lm[RIGHT_EYE_OUTER]!.x - lm[RIGHT_EYE_INNER]!.x);
      if (rightEyeW < 0.001) return false;
      const rightCX = (lm[RIGHT_EYE_INNER]!.x + lm[RIGHT_EYE_OUTER]!.x) / 2;
      const rightDX = Math.abs(lm[RIGHT_IRIS_CENTER]!.x - rightCX) / rightEyeW;
      const rightEyeH = Math.abs(lm[374]!.y - lm[386]!.y);
      const rightCY = (lm[386]!.y + lm[374]!.y) / 2;
      const rightDY = rightEyeH > 0.001 ? Math.abs(lm[RIGHT_IRIS_CENTER]!.y - rightCY) / rightEyeH : 0;

      const avgDX = (leftDX + rightDX) / 2;
      const avgDY = (leftDY + rightDY) / 2;
      return avgDX <= GAZE_THRESHOLD && avgDY <= GAZE_THRESHOLD;
    },
    []
  );

  /**
   * Smoothed eye contact with blink tolerance.
   * - Blink (<500ms eyes closed): maintains previous state
   * - Brief glance away (<600ms): maintains previous state
   * - Sustained look away (>=600ms): counts as loss
   */
  const computeEyeContact = useCallback(
    (landmarks: { x: number; y: number; z: number }[]): boolean => {
      const now = performance.now();
      const state = gazeStateRef.current;
      const ear = computeEAR(landmarks);
      const eyesClosed = ear < BLINK_EAR_THRESHOLD;

      if (eyesClosed) {
        if (state.blinkStartTimestamp === null) {
          state.blinkStartTimestamp = now;
          state.isBlinking = true;
          state.lastBlinkCounted = false;
        }
        const closedDuration = now - state.blinkStartTimestamp;
        if (closedDuration <= BLINK_MAX_DURATION_MS) {
          return state.eyeContactSmoothed; // blink — keep previous
        }
        state.isBlinking = false;
        state.eyeContactSmoothed = false;
        return false; // too long — looking away
      }

      // Eyes open — if we were blinking, count it
      if (state.isBlinking && !state.lastBlinkCounted) {
        metricsRef.current.blinkCount++;
        state.lastBlinkCounted = true;
      }
      state.blinkStartTimestamp = null;
      state.isBlinking = false;

      const rawContact = computeRawGaze(landmarks);
      if (rawContact) {
        state.gazeLostTimestamp = null;
        state.eyeContactSmoothed = true;
        return true;
      }

      // Gaze lost
      if (state.gazeLostTimestamp === null) {
        state.gazeLostTimestamp = now;
      }
      if (now - state.gazeLostTimestamp < GAZE_LOSS_MIN_DURATION_MS) {
        return state.eyeContactSmoothed; // brief glance — keep previous
      }
      state.eyeContactSmoothed = false;
      return false; // sustained loss
    },
    [computeEAR, computeRawGaze]
  );

  // Compute head pose from landmarks
  const computeHeadPose = useCallback(
    (landmarks: { x: number; y: number; z: number }[]): HeadPose => {
      // Non-null assertions safe: MediaPipe always returns 478 landmarks when face detected
      const nose = landmarks[NOSE_TIP]!;
      const chin = landmarks[CHIN]!;
      const forehead = landmarks[FOREHEAD]!;
      const leftEye = landmarks[LEFT_EYE_LEFT_CORNER]!;
      const rightEye = landmarks[RIGHT_EYE_RIGHT_CORNER]!;

      // Yaw: use nose x-offset relative to face center
      // MediaPipe gives normalized coords [0,1], face center from eye midpoint
      const eyeMidX = (leftEye.x + rightEye.x) / 2;
      const faceWidth = Math.abs(rightEye.x - leftEye.x);
      // Normalize nose offset by face width to get a ratio independent of distance
      const noseOffsetRatio = (nose.x - eyeMidX) / (faceWidth + 0.001);
      const yaw = noseOffsetRatio * 90; // scale to approximate degrees

      // Pitch: use the z-coordinates — when tilting down, nose z goes forward
      // Alternatively, use the vertical ratio of nose position between forehead and chin
      const totalFaceHeight = Math.abs(chin.y - forehead.y);
      const noseFromTop = Math.abs(nose.y - forehead.y);
      // When facing camera straight, nose is at roughly 55-65% from top
      const noseRatio = noseFromTop / (totalFaceHeight + 0.001);
      // Center around 0.6 (natural nose position) to get pitch
      const pitch = (noseRatio - 0.6) * 80; // rough degrees

      // Roll: angle of the eye line
      const eyeDeltaY = rightEye.y - leftEye.y;
      const eyeDeltaX = rightEye.x - leftEye.x;
      const roll = Math.atan2(eyeDeltaY, eyeDeltaX) * (180 / Math.PI);

      return {
        pitch: Math.round(pitch * 10) / 10,
        yaw: Math.round(yaw * 10) / 10,
        roll: Math.round(roll * 10) / 10,
      };
    },
    []
  );

  // Check face positioning in frame
  const checkFacePosition = useCallback(
    (landmarks: { x: number; y: number; z: number }[]): FacePosition => {
      const top = landmarks[FACE_OVAL_TOP]!;
      const bottom = landmarks[FACE_OVAL_BOTTOM]!;
      const left = landmarks[FACE_OVAL_LEFT]!;
      const right = landmarks[FACE_OVAL_RIGHT]!;

      const faceWidth = Math.abs(right.x - left.x);
      const faceHeight = Math.abs(bottom.y - top.y);
      const faceArea = faceWidth * faceHeight;

      const faceCenterX = (left.x + right.x) / 2;
      const faceCenterY = (top.y + bottom.y) / 2;

      // Check if face is partially out of frame
      const outOfFrame =
        top.y < 0.02 || bottom.y > 0.98 || left.x < 0.02 || right.x > 0.98;

      // Check centering (face center should be roughly in middle third)
      const centered =
        faceCenterX > 0.3 && faceCenterX < 0.7 &&
        faceCenterY > 0.2 && faceCenterY < 0.7;

      return {
        tooFar: faceArea < FACE_SIZE_MIN,
        tooClose: faceArea > FACE_SIZE_MAX,
        outOfFrame,
        centered,
      };
    },
    []
  );

  // Draw face mesh overlay on canvas
  const drawMeshOverlay = useCallback(
    (
      landmarks: { x: number; y: number; z: number }[],
      status: FaceStatus
    ) => {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video || !showMesh) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const rect = video.getBoundingClientRect();
      if (canvas.width !== rect.width || canvas.height !== rect.height) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const w = canvas.width;
      const h = canvas.height;

      // Draw face oval outline
      const color = status === "facing-camera" ? "#22c55e" : "#f59e0b";

      // Draw key contour points
      const faceOvalIndices = [
        10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
        397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
        172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10,
      ];

      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.shadowColor = color + "44";
      ctx.shadowBlur = 4;

      for (let i = 0; i < faceOvalIndices.length; i++) {
        const lm = landmarks[faceOvalIndices[i]!]!;
        const x = lm.x * w;
        const y = lm.y * h;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Draw eye outlines
      drawEyeContour(ctx, landmarks, w, h, color, "left");
      drawEyeContour(ctx, landmarks, w, h, color, "right");

      // Draw iris markers
      const leftIris = landmarks[LEFT_IRIS_CENTER]!;
      const rightIris = landmarks[RIGHT_IRIS_CENTER]!;
      drawIrisMarker(ctx, leftIris.x * w, leftIris.y * h, color);
      drawIrisMarker(ctx, rightIris.x * w, rightIris.y * h, color);

      // Draw nose tip
      const noseTip = landmarks[NOSE_TIP]!;
      ctx.beginPath();
      ctx.arc(noseTip.x * w, noseTip.y * h, 3, 0, Math.PI * 2);
      ctx.fillStyle = color + "88";
      ctx.fill();
    },
    [canvasRef, videoRef, showMesh]
  );

  // Clear canvas
  const clearOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, [canvasRef]);

  // Main processing loop
  const processFrame = useCallback(async () => {
    if (!isActiveRef.current || !faceLandmarkerRef.current) return;

    const video = videoRef.current;
    if (!video || video.readyState < 2 || video.videoWidth === 0) {
      animFrameRef.current = requestAnimationFrame(processFrame);
      return;
    }

    // Throttle to ~10 FPS for performance
    const now = performance.now();
    if (now - lastFrameTimeRef.current < 100) {
      animFrameRef.current = requestAnimationFrame(processFrame);
      return;
    }
    lastFrameTimeRef.current = now;

    try {
      const results = faceLandmarkerRef.current.detectForVideo(video, now);

      if (results.faceLandmarks && results.faceLandmarks.length > 0) {
        const landmarks = results.faceLandmarks[0] as { x: number; y: number; z: number }[];

        // Compute all metrics
        const eyeContact = computeEyeContact(landmarks);
        const headPose = computeHeadPose(landmarks);
        const facePosition = checkFacePosition(landmarks);

        // Determine status: requires BOTH head straight AND eyes looking at camera
        const headStraight =
          Math.abs(headPose.yaw) < HEAD_YAW_THRESHOLD &&
          Math.abs(headPose.pitch) < HEAD_PITCH_THRESHOLD &&
          Math.abs(headPose.roll) < HEAD_ROLL_THRESHOLD;
        const isFacing = headStraight && eyeContact;
        const status: FaceStatus = isFacing ? "facing-camera" : "turned-away";

        // Debug logging (remove after calibration)
        if (metricsRef.current.totalFrames % 10 === 0) {
          console.debug(
            `[FaceMesh] yaw=${headPose.yaw}° pitch=${headPose.pitch}° roll=${headPose.roll}° | facing=${isFacing} | eyeContact=${eyeContact}`
          );
        }

        setFaceStatus(status);
        drawMeshOverlay(landmarks, status);

        // Accumulate session metrics
        const m = metricsRef.current;
        m.totalFrames++;
        m.faceDetectedFrames++;
        if (eyeContact && isFacing) m.eyeContactFrames++;
        if (facePosition.centered) m.faceCenteredFrames++;
        m.headPoses.push(headPose);

        // Generate frame warnings
        const warnings: string[] = [];
        if (facePosition.tooFar) {
          warnings.push("Face too far — move closer to the camera");
          m.warnings.add("Face was too far from camera");
        }
        if (facePosition.tooClose) {
          warnings.push("Face too close — move back from the camera");
          m.warnings.add("Face was too close to camera");
        }
        if (facePosition.outOfFrame) {
          warnings.push("Face partially out of frame — center yourself");
          m.warnings.add("Face was partially out of frame");
        }
        if (!isFacing) {
          warnings.push("Please face the camera directly");
        }

        setCurrentWarnings(warnings);
      } else {
        // No face detected
        setFaceStatus("not-detected");
        clearOverlay();
        setCurrentWarnings(["No face detected — ensure your face is visible"]);
        metricsRef.current.totalFrames++;
        metricsRef.current.warnings.add("Face was not detected");
      }
    } catch (err) {
      // MediaPipe processing error — skip frame
      console.debug("[MediaPipe] Frame processing error:", err);
    }

    // Schedule next frame
    if (isActiveRef.current) {
      animFrameRef.current = requestAnimationFrame(processFrame);
    }
  }, [videoRef, computeEyeContact, computeHeadPose, checkFacePosition, drawMeshOverlay, clearOverlay]);

  // Check lighting from video brightness
  const checkLighting = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.readyState < 2 || !isActiveRef.current) return;

    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, 64, 64);
    const data = ctx.getImageData(0, 0, 64, 64).data;

    let brightness = 0;
    const pixels = data.length / 4;
    for (let i = 0; i < data.length; i += 4) {
      brightness += 0.299 * (data[i] ?? 0) + 0.587 * (data[i + 1] ?? 0) + 0.114 * (data[i + 2] ?? 0);
    }
    brightness /= pixels;

    if (brightness < 50) {
      setCurrentWarnings((prev) => {
        if (prev.some((w) => w.includes("lighting"))) return prev;
        return [...prev, "Low lighting — improve lighting for better tracking"];
      });
      metricsRef.current.warnings.add("Low lighting detected during session");
    }
  }, [videoRef]);

  // Start/stop processing
  useEffect(() => {
    if (isActive && isReady) {
      // Reset session metrics
      metricsRef.current = {
        totalFrames: 0,
        faceDetectedFrames: 0,
        eyeContactFrames: 0,
        faceCenteredFrames: 0,
        blinkCount: 0,
        headPoses: [],
        warnings: new Set(),
      };

      // Start processing after brief delay
      const timeout = setTimeout(() => {
        animFrameRef.current = requestAnimationFrame(processFrame);
      }, 500);

      // Periodic lighting check
      const lightingInterval = setInterval(checkLighting, 5000);

      return () => {
        clearTimeout(timeout);
        clearInterval(lightingInterval);
        if (animFrameRef.current) {
          cancelAnimationFrame(animFrameRef.current);
          animFrameRef.current = null;
        }
      };
    } else if (!isActive) {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = null;
      }
      clearOverlay();
      setCurrentWarnings([]);
    }
  }, [isActive, isReady, processFrame, checkLighting, clearOverlay]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  // Get accumulated session metrics
  const getSessionMetrics = useCallback((): SessionMetrics => {
    const m = metricsRef.current;
    const total = Math.max(m.totalFrames, 1);

    const eyeContactPercentage = Math.round((m.eyeContactFrames / total) * 1000) / 10;
    const faceVisibilityPercentage = Math.round((m.faceDetectedFrames / total) * 1000) / 10;
    const faceCenteredPercentage = Math.round((m.faceCenteredFrames / Math.max(m.faceDetectedFrames, 1)) * 1000) / 10;

    // Estimate session duration in minutes (frames at ~10 FPS)
    const sessionMinutes = total / (10 * 60);
    const blinksPerMinute = sessionMinutes > 0 ? Math.round(m.blinkCount / sessionMinutes) : 0;

    // Compute head pose statistics
    const poses = m.headPoses;
    const count = Math.max(poses.length, 1);

    const avgPitch = poses.reduce((s, p) => s + p.pitch, 0) / count;
    const avgYaw = poses.reduce((s, p) => s + p.yaw, 0) / count;
    const avgRoll = poses.reduce((s, p) => s + p.roll, 0) / count;

    const stdPitch = Math.sqrt(
      poses.reduce((s, p) => s + (p.pitch - avgPitch) ** 2, 0) / count
    );
    const stdYaw = Math.sqrt(
      poses.reduce((s, p) => s + (p.yaw - avgYaw) ** 2, 0) / count
    );
    const stdRoll = Math.sqrt(
      poses.reduce((s, p) => s + (p.roll - avgRoll) ** 2, 0) / count
    );

    const headStability: "stable" | "excessive" =
      stdPitch > STABILITY_THRESHOLD ||
      stdYaw > STABILITY_THRESHOLD ||
      stdRoll > STABILITY_THRESHOLD
        ? "excessive"
        : "stable";

    // Compute Presentation Presence Score (0-100)
    // Weighted composite: eye contact 40%, face visibility 20%, centering 20%, head stability 20%
    const stabilityScore = headStability === "stable" ? 100 : Math.max(0, 100 - (Math.max(stdPitch, stdYaw, stdRoll) - STABILITY_THRESHOLD) * 10);
    const presentationPresenceScore = Math.round(
      eyeContactPercentage * 0.4 +
      faceVisibilityPercentage * 0.2 +
      faceCenteredPercentage * 0.2 +
      stabilityScore * 0.2
    );

    return {
      totalFrames: m.totalFrames,
      faceDetectedFrames: m.faceDetectedFrames,
      faceVisibilityPercentage,
      eyeContactFrames: m.eyeContactFrames,
      eyeContactPercentage,
      faceCenteredPercentage,
      blinkCount: m.blinkCount,
      blinksPerMinute,
      headPoseHistory: poses,
      avgPitch: Math.round(avgPitch * 10) / 10,
      avgYaw: Math.round(avgYaw * 10) / 10,
      avgRoll: Math.round(avgRoll * 10) / 10,
      stdPitch: Math.round(stdPitch * 10) / 10,
      stdYaw: Math.round(stdYaw * 10) / 10,
      stdRoll: Math.round(stdRoll * 10) / 10,
      headStability,
      presentationPresenceScore: Math.min(100, Math.max(0, presentationPresenceScore)),
      warnings: Array.from(m.warnings),
    };
  }, []);

  return {
    faceStatus,
    isReady,
    currentWarnings,
    getSessionMetrics,
  };
}

// --- Drawing helpers ---

function drawEyeContour(
  ctx: CanvasRenderingContext2D,
  landmarks: { x: number; y: number; z: number }[],
  w: number,
  h: number,
  color: string,
  side: "left" | "right"
) {
  // Simplified eye contour indices
  const leftEyeIndices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246, 33];
  const rightEyeIndices = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398, 362];

  const indices = side === "left" ? leftEyeIndices : rightEyeIndices;

  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;

  for (let i = 0; i < indices.length; i++) {
    const lm = landmarks[indices[i]!]!;
    const x = lm.x * w;
    const y = lm.y * h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function drawIrisMarker(ctx: CanvasRenderingContext2D, x: number, y: number, color: string) {
  ctx.beginPath();
  ctx.arc(x, y, 4, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = "white";
  ctx.lineWidth = 1;
  ctx.stroke();
}
