import { Account, formatCurrency } from "@/api/monarch";

const TYPE_LABEL: Record<Account["type"], string> = {
  depository: "Cash",
  investment: "Investments",
  credit: "Credit",
  loan: "Loans",
  real_estate: "Real estate",
  other: "Other",
};

const TYPE_ORDER: Account["type"][] = [
  "depository",
  "investment",
  "real_estate",
  "other",
  "credit",
  "loan",
];

export function AccountTable({ accounts }: { accounts: Account[] }) {
  const visible = accounts.filter((a) => !a.is_hidden);
  const grouped = new Map<Account["type"], Account[]>();
  for (const a of visible) {
    if (!grouped.has(a.type)) grouped.set(a.type, []);
    grouped.get(a.type)!.push(a);
  }
  return (
    <div className="space-y-6">
      {TYPE_ORDER.filter((t) => grouped.has(t)).map((type) => {
        const rows = grouped.get(type)!;
        const subtotal = rows.reduce((sum, r) => sum + r.balance_current, 0);
        return (
          <div key={type} className="rounded border border-slate-200 bg-white">
            <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
              <h3 className="text-sm font-semibold">{TYPE_LABEL[type]}</h3>
              <span className="text-sm text-slate-600">{formatCurrency(subtotal)}</span>
            </div>
            <table className="w-full text-sm">
              <tbody>
                {rows.map((a) => (
                  <tr key={a.id} className="border-t border-slate-50">
                    <td className="px-4 py-2">{a.name}</td>
                    <td className="px-4 py-2 text-slate-500">{a.institution ?? ""}</td>
                    <td className="px-4 py-2 text-right">
                      {formatCurrency(a.balance_current, a.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}
