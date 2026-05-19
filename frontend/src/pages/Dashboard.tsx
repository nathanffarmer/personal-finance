import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export default function Dashboard() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ status: string }>("/api/health"),
  });

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Dashboard</h2>
      <div className="rounded border border-slate-200 bg-white p-4">
        <div className="text-sm text-slate-500">Backend health</div>
        <div className="text-xl mt-1">
          {health.isLoading ? "…" : health.data?.status ?? "unknown"}
        </div>
      </div>
      <p className="mt-6 text-sm text-slate-500">
        Account list and net-worth KPIs ship in Milestone 2.
      </p>
    </div>
  );
}
