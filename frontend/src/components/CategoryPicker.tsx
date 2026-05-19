import { Category } from "@/api/monarch";

export function CategoryPicker({
  value,
  categories,
  onChange,
}: {
  value: string | null;
  categories: Category[];
  onChange: (categoryId: string) => void;
}) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="text-sm border border-slate-300 rounded px-2 py-1 bg-white"
    >
      <option value="">— Uncategorized —</option>
      {categories.map((c) => (
        <option key={c.id} value={c.id}>
          {c.group ? `${c.group} · ` : ""}
          {c.name}
        </option>
      ))}
    </select>
  );
}
