import { useState } from "react";
import Topbar from "../layout/Topbar";
import { Card } from "../components/Card";
import { LoadingBlock, ErrorBlock, EmptyBlock } from "../components/StatusStates";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "../api/dashboard";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function Analytics() {
  const [filter, setFilter] = useState({ range: "7d", groupBy: "crime_head" });

  const { data: trends, isLoading: loading, error, refetch } = useQuery({
    queryKey: ["analytics", "trends", filter],
    queryFn: () => dashboardApi.getTrends(filter),
  });

  return (
    <div>
      <Topbar title="Crime Analytics" subtitle="Explore trends and patterns" />
      <div className="p-8 space-y-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-ink-600">Time range:</span>
            <select
              value={filter.range}
              onChange={(e) => setFilter({ ...filter, range: e.target.value })}
              className="rounded-lg border border-ink-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="1d">Last 24h</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="1y">Last year</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-ink-600">Group by:</span>
            <select
              value={filter.groupBy}
              onChange={(e) => setFilter({ ...filter, groupBy: e.target.value })}
              className="rounded-lg border border-ink-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="crime_head">Crime Type</option>
              <option value="police_station">Police Station</option>
              <option value="district">District</option>
              <option value="date">Date</option>
            </select>
          </div>
          <button onClick={() => refetch()} className="btn-secondary">Refresh</button>
        </div>

        <Card title="Trend Analysis">
          {loading && <LoadingBlock lines={8} />}
          {error && <ErrorBlock error={error} />}
          {!loading && !error && !trends && <EmptyBlock label="No data available." />}
          {!loading && !error && trends && (
            <div>
              <div className="h-60 relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={trends.groups}
                      dataKey="count"
                      nameKey="label"
                      innerRadius={60}
                      outerRadius={90}
                    >
                      {trends.groups.map((_, i) => (
                        <Cell key={i} fill={ `hsl(${(i * 45) % 360}, 70%, 50%)` } />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value, name) => `${name}: ${value}`} />
                    <Legend verticalAlign="top" height={36} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <table className="w-full mt-4 text-sm">
                <thead>
                  <tr className="text-left text-ink-500 border-b border-ink-100">
                    <th className="py-2">Group</th>
                    <th className="py-2">Count</th>
                    <th className="py-2">Percentage</th>
                  </tr>
                </thead>
                <tbody>
                  {trends.groups.map((g) => (
                    <tr key={g.label} className="border-b border-ink-100">
                      <td className="py-2">{g.label}</td>
                      <td className="py-2">{g.count}</td>
                      <td className="py-2">{g.pct != null ? `${g.pct}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}