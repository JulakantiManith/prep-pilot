import { z } from "zod";

export const interviewSetupSchema = z.object({
  interviewType: z.enum(["hr", "technical", "behavioral", "custom", "resume_based"], {
    message: "Please select an interview type",
  }),
  role: z
    .string()
    .min(1, "Role is required")
    .max(100, "Role must be at most 100 characters"),
  topic: z.string().optional(),
  difficulty: z.enum(["beginner", "intermediate", "advanced"], {
    message: "Please select a difficulty level",
  }),
  numQuestions: z
    .number()
    .min(1, "Must have at least 1 question")
    .max(20, "Maximum 20 questions"),
});

export const technicalSetupSchema = z.object({
  topic: z.enum([
    "Data Structures",
    "Algorithms",
    "OS",
    "DBMS",
    "CN",
    "OOP",
    "Java",
    "Python",
    "JavaScript",
    "React",
    "Node.js",
    "Cloud Computing",
  ], {
    message: "Please select a technical topic",
  }),
  difficulty: z.enum(["beginner", "intermediate", "advanced"], {
    message: "Please select a difficulty level",
  }),
  role: z
    .string()
    .min(1, "Role is required")
    .max(100, "Role must be at most 100 characters"),
  numQuestions: z
    .number()
    .min(1, "Must have at least 1 question")
    .max(20, "Maximum 20 questions"),
});

export type InterviewSetupFormData = z.infer<typeof interviewSetupSchema>;
export type TechnicalSetupFormData = z.infer<typeof technicalSetupSchema>;

export const TECHNICAL_TOPICS = [
  "Data Structures",
  "Algorithms",
  "OS",
  "DBMS",
  "CN",
  "OOP",
  "Java",
  "Python",
  "JavaScript",
  "React",
  "Node.js",
  "Cloud Computing",
] as const;

export type TechnicalTopic = (typeof TECHNICAL_TOPICS)[number];
