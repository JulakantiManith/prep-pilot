import { ProfileForm } from "../components/ProfileForm";
import { ResumeUpload } from "../components/ResumeUpload";

export function ProfilePage() {
  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Profile</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your profile information and resume.
        </p>
      </div>

      <section aria-labelledby="profile-info-heading" className="space-y-4">
        <h2 id="profile-info-heading" className="text-lg font-semibold text-foreground">
          Profile Information
        </h2>
        <ProfileForm />
      </section>

      <section aria-labelledby="resume-heading" className="space-y-4">
        <h2 id="resume-heading" className="text-lg font-semibold text-foreground">
          Resume
        </h2>
        <ResumeUpload />
      </section>
    </div>
  );
}
