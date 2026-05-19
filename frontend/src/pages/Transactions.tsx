import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Transaction, formatCurrency, monarchApi } from "@/api/monarch";
import { CategoryPicker } from "@/components/CategoryPicker";

export default function Transactions() {
  const qc = useQueryClient();
  const [limit] = useState(100);
  const [offset, setOffset] = useState(0);
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkCategory, setBulkCategory] = useState("");

  const txQuery = useQuery({
    queryKey: ["transactions", { limit, offset }],
    queryFn: () => monarchApi.transactions({ limit, offset }),
  });
  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: monarchApi.categories,
  });

  const update = useMutation({
    mutationFn: (args: { id: string; category_id: string }) =>
      monarchApi.updateTransaction(args.id, { category_id: args.category_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });

  const bulkUpdate = useMutation({
    mutationFn: (items: { id: string; category_id: string }[]) =>
      monarchApi.categorizeBulk(items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      setSelected(new Set());
    },
  });

  const rows = (txQuery.data ?? []).filter(
    (t) => !uncategorizedOnly || t.category_id == null,
  );

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  return (
    <div className="max-w-6xl">
      <h2 className="text-2xl font-semibold mb-4">Transactions</h2>

      <div className="flex items-center gap-4 mb-4">
        <label className="text-sm flex items-center gap-2">
          <input
            type="checkbox"
            checked={uncategorizedOnly}
            onChange={(e) => setUncategorizedOnly(e.target.checked)}
          />
          Uncategorized only
        </label>
        <div className="flex items-center gap-2 text-sm">
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            className="px-2 py-1 border border-slate-300 rounded disabled:opacity-40"
          >
            ‹ Prev
          </button>
          <span className="text-slate-600">
            Offset {offset}–{offset + limit}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            className="px-2 py-1 border border-slate-300 rounded"
          >
            Next ›
          </button>
        </div>
      </div>

      {selected.size > 0 && (
        <div className="mb-4 rounded border border-slate-300 bg-slate-50 px-3 py-2 flex items-center gap-3">
          <span className="text-sm">{selected.size} selected</span>
          <select
            value={bulkCategory}
            onChange={(e) => setBulkCategory(e.target.value)}
            className="text-sm border border-slate-300 rounded px-2 py-1 bg-white"
          >
            <option value="">Choose category…</option>
            {(categoriesQuery.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.group ? `${c.group} · ` : ""}
                {c.name}
              </option>
            ))}
          </select>
          <button
            disabled={!bulkCategory || bulkUpdate.isPending}
            onClick={() =>
              bulkUpdate.mutate(
                [...selected].map((id) => ({ id, category_id: bulkCategory })),
              )
            }
            className="px-3 py-1 text-sm rounded bg-ink text-white disabled:opacity-40"
          >
            Apply
          </button>
          <button
            onClick={() => setSelected(new Set())}
            className="text-sm text-slate-600 underline"
          >
            Clear
          </button>
        </div>
      )}

      <div className="rounded border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr className="text-left">
              <th className="px-3 py-2 w-8"></th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Merchant</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t: Transaction) => (
              <tr key={t.id} className="border-t border-slate-100">
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selected.has(t.id)}
                    onChange={() => toggle(t.id)}
                  />
                </td>
                <td className="px-3 py-2 text-slate-600">{t.date}</td>
                <td className="px-3 py-2">{t.merchant || t.description}</td>
                <td className="px-3 py-2">
                  <CategoryPicker
                    value={t.category_id}
                    categories={categoriesQuery.data ?? []}
                    onChange={(category_id) =>
                      update.mutate({ id: t.id, category_id })
                    }
                  />
                </td>
                <td
                  className={`px-3 py-2 text-right tabular-nums ${
                    t.amount < 0 ? "text-rose-600" : "text-emerald-700"
                  }`}
                >
                  {formatCurrency(t.amount)}
                </td>
              </tr>
            ))}
            {!txQuery.isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                  No transactions match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
