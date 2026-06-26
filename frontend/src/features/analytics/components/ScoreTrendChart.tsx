import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { ScoreTrend } from "../services/analyticsService";

interface ScoreTrendChartProps {
  overallScores: ScoreTrend[];
  confidenceScores: ScoreTrend[];
  communicationScores: ScoreTrend[];
}

interface ChartColors {
  overall: string;
  confidence: string;
  communication: string;
  grid: string;
  tick: string;
  cardBg: string;
  cardFg: string;
}

function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>({
    overall: "#3b82f6",
    confidence: "#10b981",
    communication: "#f59e0b",
    grid: "#e5e7eb",
    tick: "#6b7280",
    cardBg: "#ffffff",
    cardFg: "#111827",
  });

  useEffect(() => {
    function updateColors() {
      const styles = getComputedStyle(document.documentElement);
      setColors({
        overall: styles.getPropertyValue("--color-chart-1").trim() || "#3b82f6",
        confidence: styles.getPropertyValue("--color-chart-2").trim() || "#10b981",
        communication: styles.getPropertyValue("--color-chart-3").trim() || "#f59e0b",
        grid: styles.getPropertyValue("--color-border").trim() || "#e5e7eb",
        tick: styles.getPropertyValue("--color-muted-foreground").trim() || "#6b7280",
        cardBg: styles.getPropertyValue("--color-card").trim() || "#ffffff",
        cardFg: styles.getPropertyValue("--color-card-foreground").trim() || "#111827",
      });
    }

    updateColors();

    const observer = new MutationObserver(updateColors);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => observer.disconnect();
  }, []);

  return colors;
}

function formatDateLabel(dateStr: string): string {
  // Handle week format "YYYY-Wnn" — compute the Monday of that ISO week
  if (dateStr.includes("-W")) {
    const [yearStr, weekStr] = dateStr.split("-W");
    const year = parseInt(yearStr ?? "0", 10);
    const week = parseInt(weekStr ?? "0", 10);
    // Jan 4 is always in ISO week 1
    const jan4 = new Date(year, 0, 4);
    const dayOfWeek = jan4.getDay() || 7; // Mon=1..Sun=7
    const monday = new Date(jan4);
    monday.setDate(jan4.getDate() - dayOfWeek + 1 + (week - 1) * 7);
    return monday.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  // Handle month format "YYYY-MM"
  if (/^\d{4}-\d{2}$/.test(dateStr)) {
    const date = new Date(dateStr + "-01T00:00:00");
    return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
  }
  // Handle date format "YYYY-MM-DD"
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function ScoreTrendChart({
  overallScores,
  confidenceScores,
  communicationScores,
}: ScoreTrendChartProps) {
  const colors = useChartColors();

  // Merge all score series into unified data points by date
  const dateSet = new Set<string>();
  overallScores.forEach((s) => dateSet.add(s.date));
  confidenceScores.forEach((s) => dateSet.add(s.date));
  communicationScores.forEach((s) => dateSet.add(s.date));

  const dates = Array.from(dateSet).sort();

  const overallMap = new Map(overallScores.map((s) => [s.date, s.averageScore]));
  const confidenceMap = new Map(confidenceScores.map((s) => [s.date, s.averageScore]));
  const communicationMap = new Map(communicationScores.map((s) => [s.date, s.averageScore]));

  const chartData = dates.map((date) => ({
    label: formatDateLabel(date),
    overall: overallMap.get(date) ?? null,
    confidence: confidenceMap.get(date) ?? null,
    communication: communicationMap.get(date) ?? null,
  }));

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Score Trends</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Track your overall, confidence, and communication scores over time
      </p>

      {chartData.length === 0 ? (
        <div className="mt-4 flex h-48 items-center justify-center">
          <p className="text-sm text-muted-foreground">
            No trend data available for this period.
          </p>
        </div>
      ) : (
        <div className="mt-4 h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="overallGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.overall} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={colors.overall} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.confidence} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={colors.confidence} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="communicationGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.communication} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={colors.communication} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: colors.tick }}
                stroke={colors.grid}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 12, fill: colors.tick }}
                stroke={colors.grid}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: `1px solid ${colors.grid}`,
                  backgroundColor: colors.cardBg,
                  color: colors.cardFg,
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
                labelStyle={{ fontWeight: 600, color: colors.cardFg, marginBottom: "4px" }}
                formatter={(value, name) => {
                  const labels: Record<string, string> = {
                    overall: "Overall",
                    confidence: "Confidence",
                    communication: "Communication",
                  };
                  return [`${Math.round(Number(value))}%`, labels[String(name)] || String(name)];
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "12px" }}
                formatter={(value: string) => {
                  const labels: Record<string, string> = {
                    overall: "Overall",
                    confidence: "Confidence",
                    communication: "Communication",
                  };
                  return labels[value] || value;
                }}
              />
              <Area
                type="monotone"
                dataKey="overall"
                stroke={colors.overall}
                strokeWidth={2}
                fill="url(#overallGradient)"
                dot={{ r: 3, fill: colors.overall }}
                activeDot={{ r: 5, fill: colors.overall }}
                connectNulls
                animationDuration={1000}
                animationEasing="ease-in-out"
              />
              <Area
                type="monotone"
                dataKey="confidence"
                stroke={colors.confidence}
                strokeWidth={2}
                fill="url(#confidenceGradient)"
                dot={{ r: 3, fill: colors.confidence }}
                activeDot={{ r: 5, fill: colors.confidence }}
                connectNulls
                animationDuration={1000}
                animationEasing="ease-in-out"
              />
              <Area
                type="monotone"
                dataKey="communication"
                stroke={colors.communication}
                strokeWidth={2}
                fill="url(#communicationGradient)"
                dot={{ r: 3, fill: colors.communication }}
                activeDot={{ r: 5, fill: colors.communication }}
                connectNulls
                animationDuration={1000}
                animationEasing="ease-in-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
