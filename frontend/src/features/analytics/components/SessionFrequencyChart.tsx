import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ProgressDataPoint } from "../services/analyticsService";

interface SessionFrequencyChartProps {
  dataPoints: ProgressDataPoint[];
}

interface ChartColors {
  bar: string;
  grid: string;
  tick: string;
  cardBg: string;
  cardFg: string;
}

function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>({
    bar: "#3b82f6",
    grid: "#e5e7eb",
    tick: "#6b7280",
    cardBg: "#ffffff",
    cardFg: "#111827",
  });

  useEffect(() => {
    function updateColors() {
      const styles = getComputedStyle(document.documentElement);
      setColors({
        bar: styles.getPropertyValue("--color-chart-1").trim() || "#3b82f6",
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

function formatPeriodLabel(period: string): string {
  // Handle week format "YYYY-Wnn" — show the Monday date of that ISO week
  if (period.includes("-W")) {
    const [yearStr, weekStr] = period.split("-W");
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
  if (/^\d{4}-\d{2}$/.test(period)) {
    const date = new Date(period + "-01T00:00:00");
    return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
  }
  // Handle date format "YYYY-MM-DD"
  const date = new Date(period + "T00:00:00");
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function SessionFrequencyChart({ dataPoints }: SessionFrequencyChartProps) {
  const colors = useChartColors();

  const chartData = dataPoints.map((item) => ({
    label: formatPeriodLabel(item.period),
    sessionCount: item.sessionCount,
    averageScore: item.averageScore,
  }));

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold">Session Frequency</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Number of practice sessions per period
      </p>

      {chartData.length === 0 ? (
        <div className="mt-4 flex h-48 items-center justify-center">
          <p className="text-sm text-muted-foreground">
            No session data available for this period.
          </p>
        </div>
      ) : (
        <div className="mt-4 h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.bar} stopOpacity={0.9} />
                  <stop offset="95%" stopColor={colors.bar} stopOpacity={0.6} />
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
                allowDecimals={false}
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
                  if (String(name) === "sessionCount") return [`${value}`, "Sessions"];
                  return [`${value}`, String(name)];
                }}
                cursor={{ fill: colors.bar, opacity: 0.1 }}
              />
              <Bar
                dataKey="sessionCount"
                fill="url(#barGradient)"
                radius={[4, 4, 0, 0]}
                maxBarSize={48}
                animationDuration={1000}
                animationEasing="ease-in-out"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
