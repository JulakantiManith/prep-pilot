import { useState } from "react";
import { Plus, Trash2, AlertTriangle } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";
import type {
  ExtractedResumeData,
  ExtractedProject,
  ExtractedExperience,
  ExtractedEducation,
} from "../services/resumeInterviewService";

interface ResumeDataFormProps {
  data: ExtractedResumeData;
  confidence: number | null;
  onChange: (data: ExtractedResumeData) => void;
}

const LOW_CONFIDENCE_THRESHOLD = 0.7;

export function ResumeDataForm({ data, confidence, onChange }: ResumeDataFormProps) {
  const isLowConfidence = confidence !== null && confidence < LOW_CONFIDENCE_THRESHOLD;

  return (
    <div className="space-y-6">
      {isLowConfidence && (
        <div
          className="flex items-start gap-2 rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3 text-sm text-yellow-700 dark:text-yellow-400"
          role="alert"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Low extraction confidence ({Math.round((confidence ?? 0) * 100)}%).
            Please review and correct the highlighted fields below.
          </span>
        </div>
      )}

      <SkillsSection
        skills={data.skills}
        isHighlighted={isLowConfidence}
        onChange={(skills) => onChange({ ...data, skills })}
      />

      <ProjectsSection
        projects={data.projects}
        isHighlighted={isLowConfidence}
        onChange={(projects) => onChange({ ...data, projects })}
      />

      <ExperienceSection
        experience={data.experience}
        isHighlighted={isLowConfidence}
        onChange={(experience) => onChange({ ...data, experience })}
      />

      <EducationSection
        education={data.education}
        isHighlighted={isLowConfidence}
        onChange={(education) => onChange({ ...data, education })}
      />
    </div>
  );
}

// --- Skills Section ---

interface SkillsSectionProps {
  skills: string[];
  isHighlighted: boolean;
  onChange: (skills: string[]) => void;
}

function SkillsSection({ skills, isHighlighted, onChange }: SkillsSectionProps) {
  const [newSkill, setNewSkill] = useState("");

  const addSkill = () => {
    const trimmed = newSkill.trim();
    if (trimmed && !skills.includes(trimmed)) {
      onChange([...skills, trimmed]);
      setNewSkill("");
    }
  };

  const removeSkill = (index: number) => {
    onChange(skills.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addSkill();
    }
  };

  return (
    <div
      className={cn(
        "space-y-3 rounded-md border p-4",
        isHighlighted ? "border-yellow-500/50 bg-yellow-500/5" : "border-input"
      )}
    >
      <h3 className="text-sm font-medium text-foreground">Skills</h3>
      <div className="flex flex-wrap gap-2">
        {skills.map((skill, index) => (
          <span
            key={index}
            className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
          >
            {skill}
            <button
              type="button"
              onClick={() => removeSkill(index)}
              className="ml-1 rounded-full p-0.5 hover:bg-primary/20"
              aria-label={`Remove ${skill}`}
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={newSkill}
          onChange={(e) => setNewSkill(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a skill..."
          className="flex h-9 flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button type="button" variant="outline" size="sm" onClick={addSkill}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// --- Projects Section ---

interface ProjectsSectionProps {
  projects: ExtractedProject[];
  isHighlighted: boolean;
  onChange: (projects: ExtractedProject[]) => void;
}

function ProjectsSection({ projects, isHighlighted, onChange }: ProjectsSectionProps) {
  const updateProject = (index: number, field: keyof ExtractedProject, value: string) => {
    const updated = projects.map((p, i) =>
      i === index ? { ...p, [field]: value } : p
    );
    onChange(updated);
  };

  const addProject = () => {
    onChange([...projects, { name: "", description: "", technologies: "" }]);
  };

  const removeProject = (index: number) => {
    onChange(projects.filter((_, i) => i !== index));
  };

  return (
    <div
      className={cn(
        "space-y-3 rounded-md border p-4",
        isHighlighted ? "border-yellow-500/50 bg-yellow-500/5" : "border-input"
      )}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">Projects</h3>
        <Button type="button" variant="outline" size="sm" onClick={addProject}>
          <Plus className="mr-1 h-3 w-3" /> Add
        </Button>
      </div>
      {projects.length === 0 && (
        <p className="text-sm text-muted-foreground">No projects extracted.</p>
      )}
      {projects.map((project, index) => (
        <div key={index} className="space-y-2 rounded-md border border-input bg-background p-3">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium text-muted-foreground">Project {index + 1}</span>
            <button
              type="button"
              onClick={() => removeProject(index)}
              className="text-muted-foreground hover:text-destructive"
              aria-label={`Remove project ${index + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
          <input
            type="text"
            value={project.name}
            onChange={(e) => updateProject(index, "name", e.target.value)}
            placeholder="Project name"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <textarea
            value={project.description}
            onChange={(e) => updateProject(index, "description", e.target.value)}
            placeholder="Description"
            rows={2}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <input
            type="text"
            value={project.technologies}
            onChange={(e) => updateProject(index, "technologies", e.target.value)}
            placeholder="Technologies (comma-separated)"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
      ))}
    </div>
  );
}

// --- Experience Section ---

interface ExperienceSectionProps {
  experience: ExtractedExperience[];
  isHighlighted: boolean;
  onChange: (experience: ExtractedExperience[]) => void;
}

function ExperienceSection({ experience, isHighlighted, onChange }: ExperienceSectionProps) {
  const updateExperience = (index: number, field: keyof ExtractedExperience, value: string) => {
    const updated = experience.map((e, i) =>
      i === index ? { ...e, [field]: value } : e
    );
    onChange(updated);
  };

  const addExperience = () => {
    onChange([...experience, { title: "", company: "", duration: "", description: "" }]);
  };

  const removeExperience = (index: number) => {
    onChange(experience.filter((_, i) => i !== index));
  };

  return (
    <div
      className={cn(
        "space-y-3 rounded-md border p-4",
        isHighlighted ? "border-yellow-500/50 bg-yellow-500/5" : "border-input"
      )}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">Experience</h3>
        <Button type="button" variant="outline" size="sm" onClick={addExperience}>
          <Plus className="mr-1 h-3 w-3" /> Add
        </Button>
      </div>
      {experience.length === 0 && (
        <p className="text-sm text-muted-foreground">No experience extracted.</p>
      )}
      {experience.map((exp, index) => (
        <div key={index} className="space-y-2 rounded-md border border-input bg-background p-3">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium text-muted-foreground">Experience {index + 1}</span>
            <button
              type="button"
              onClick={() => removeExperience(index)}
              className="text-muted-foreground hover:text-destructive"
              aria-label={`Remove experience ${index + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              value={exp.title}
              onChange={(e) => updateExperience(index, "title", e.target.value)}
              placeholder="Job title"
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <input
              type="text"
              value={exp.company}
              onChange={(e) => updateExperience(index, "company", e.target.value)}
              placeholder="Company"
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <input
            type="text"
            value={exp.duration}
            onChange={(e) => updateExperience(index, "duration", e.target.value)}
            placeholder="Duration (e.g., Jan 2022 - Present)"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <textarea
            value={exp.description}
            onChange={(e) => updateExperience(index, "description", e.target.value)}
            placeholder="Description"
            rows={2}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
      ))}
    </div>
  );
}

// --- Education Section ---

interface EducationSectionProps {
  education: ExtractedEducation[];
  isHighlighted: boolean;
  onChange: (education: ExtractedEducation[]) => void;
}

function EducationSection({ education, isHighlighted, onChange }: EducationSectionProps) {
  const updateEducation = (index: number, field: keyof ExtractedEducation, value: string) => {
    const updated = education.map((e, i) =>
      i === index ? { ...e, [field]: value } : e
    );
    onChange(updated);
  };

  const addEducation = () => {
    onChange([...education, { degree: "", institution: "", year: "" }]);
  };

  const removeEducation = (index: number) => {
    onChange(education.filter((_, i) => i !== index));
  };

  return (
    <div
      className={cn(
        "space-y-3 rounded-md border p-4",
        isHighlighted ? "border-yellow-500/50 bg-yellow-500/5" : "border-input"
      )}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">Education</h3>
        <Button type="button" variant="outline" size="sm" onClick={addEducation}>
          <Plus className="mr-1 h-3 w-3" /> Add
        </Button>
      </div>
      {education.length === 0 && (
        <p className="text-sm text-muted-foreground">No education extracted.</p>
      )}
      {education.map((edu, index) => (
        <div key={index} className="space-y-2 rounded-md border border-input bg-background p-3">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium text-muted-foreground">Education {index + 1}</span>
            <button
              type="button"
              onClick={() => removeEducation(index)}
              className="text-muted-foreground hover:text-destructive"
              aria-label={`Remove education ${index + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              value={edu.degree}
              onChange={(e) => updateEducation(index, "degree", e.target.value)}
              placeholder="Degree"
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <input
              type="text"
              value={edu.institution}
              onChange={(e) => updateEducation(index, "institution", e.target.value)}
              placeholder="Institution"
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <input
            type="text"
            value={edu.year}
            onChange={(e) => updateEducation(index, "year", e.target.value)}
            placeholder="Year (e.g., 2023)"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
      ))}
    </div>
  );
}
