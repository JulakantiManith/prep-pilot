import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { WeeklyProgress, TimeRange } from "../services/dashboardService";

interface WeeklyChartProps {
  data: WeeklyProgress[];
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
}

interface ChartColors {
  line: string;
  grid: string;
  tick: string;
  cardBg: string;
  cardFg: string;
}

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: "daily", label: "Today" },
  { value: "weekly", label: "This Week" },
  { value: "monthly", label: "1 Month" },
  { value: "3months", label: "3 Months" },
  { value: "yearly", label: "1 Year" },
];

function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>({
    line: "#3b82f6",
    grid: "#e5e7eb",
    tick: "#6b7280",
    cardBg: "#ffffff",
    cardFg: "#111827",
  });

  useEffect(() => {
    function updateColors() {
      const styles = getComputedStyle(document.documentElement);
      setColors({
        line: styles.getPropertyValue("--color-chart-1").trim() || "#3b82f6",
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

function formatDateLabel(dateStr: string, timeRange: TimeRange): string {
  const date = new Date(dateStr + "T00:00:00");

  if (timeRange === "daily") {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  if (timeRange === "weekly") {
    return date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  }
  if (timeRange === "monthly") {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  // 3months, yearly — show month + day abbreviated
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function getChartTitle(timeRange: TimeRange): string {
  switch (timeRange) {
    case "daily":
      return "Today's Progress";
    case "weekly":
      return "Weekly Progress";
    case "monthly":
      return "Monthly Progress";
    case "3months":
      return "3-Month Progress";
    case "yearly":
      return "Yearly Progress";
  }
}

export function WeeklyChart({ data, timeRange, onTimeRangeChange }: WeeklyChartProps) {
  const colors = useChartColors();

  const chartData = data.map((item) => ({
    ...item,
    label: formatDateLabel(item.date, timeRange),
  }));

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-lg font-semibold">{getChartTitle(timeRange)}</h3>
        <select
          value={timeRange}
          onChange={(e) => onTimeRangeChange(e.target.value as TimeRange)}
          className="rounded-md border bg-background px-3 py-1.5 text-sm font-medium text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {TIME_RANGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {data.length === 0 ? (
        <div className="mt-4 flex h-48 items-center justify-center">
          <p className="text-sm text-muted-foreground">
            No data for this period yet. Complete a session to see your progress.
          </p>
        </div>
      ) : (
        <div className="mt-4 h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
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
                }}
                labelStyle={{ fontWeight: 600, color: colors.cardFg }}
                formatter={(value: number) => [`${Math.round(value)}%`, "Avg Score"]}
              />
              <Line
                type="monotone"
                dataKey="averageScore"
                stroke={colors.line}
                strokeWidth={2}
                dot={{ r: 4, fill: colors.line }}
                activeDot={{ r: 6, fill: colors.line }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
