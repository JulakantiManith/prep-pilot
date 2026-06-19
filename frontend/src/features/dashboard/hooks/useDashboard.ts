import { useQuery } from "@tanstack/react-query";
import { getDashboardData } from "../services/dashboardService";
import type { TimeRange } from "../services/dashboardService";

const DASHBOARD_QUERY_KEY = "dashboard" as const;

export function useDashboard(timeRange: TimeRange = "weekly") {
  return useQuery({
    queryKey: [DASHBOARD_QUERY_KEY, timeRange],
    queryFn: () => getDashboardData(timeRange),
  });
}
