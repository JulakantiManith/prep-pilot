import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Button } from "@/shared/components/ui/button";

export function OnboardingState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border bg-card p-12 text-center shadow-sm">
      <Sparkles className="h-12 w-12 text-primary" />
      <h2 className="mt-4 text-2xl font-bold">Welcome to your Dashboard</h2>
      <p className="mt-2 max-w-md text-muted-foreground">
        Start your first practice session to see your performance metrics,
        progress charts, and session history here.
      </p>
      <Button asChild className="mt-6" size="lg">
        <Link to="/interview">Start Your First Session</Link>
      </Button>
    </div>
  );
}
