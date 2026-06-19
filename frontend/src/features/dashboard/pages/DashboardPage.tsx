import { useState } from "react";
import { useDashboard } from "../hooks/useDashboard";
import { MetricsCards } from "../components/MetricsCards";
import { WeeklyChart } from "../components/WeeklyChart";
import { RecentSessions } from "../components/RecentSessions";
import { OnboardingState } from "../components/OnboardingState";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import type { TimeRange } from "../services/dashboardService";

export function DashboardPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>("weekly");
  const { data, isLoading, isError, error, refetch } = useDashboard(timeRange);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner label="Loading dashboard..." />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorMessage
        message={
          error instanceof Error
            ? error.message
            : "Failed to load dashboard data."
        }
        retry={() => void refetch()}
      />
    );
  }

  if (!data) {
    return null;
  }

  if (!data.hasSessions) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <OnboardingState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <MetricsCards overview={data.overview} />
      <div className="grid gap-6 lg:grid-cols-2">
        <WeeklyChart
          data={data.weeklyProgress}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />
        <RecentSessions sessions={data.recentSessions} />
      </div>
    </div>
  );
}
