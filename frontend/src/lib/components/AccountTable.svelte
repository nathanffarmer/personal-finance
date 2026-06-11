<script lang="ts">
  import { type Account, formatCurrency } from "$api/monarch";

  let { accounts }: { accounts: Account[] } = $props();

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

  let groups = $derived.by(() => {
    const visible = accounts.filter((a) => !a.is_hidden);
    const grouped = new Map<Account["type"], Account[]>();
    for (const a of visible) {
      if (!grouped.has(a.type)) grouped.set(a.type, []);
      grouped.get(a.type)!.push(a);
    }
    return TYPE_ORDER.filter((t) => grouped.has(t)).map((type) => {
      const rows = grouped.get(type)!;
      const subtotal = rows.reduce((sum, r) => sum + r.balance_current, 0);
      return { type, rows, subtotal };
    });
  });
</script>

<div class="space-y-6">
  {#each groups as group (group.type)}
    <div class="rounded border border-slate-200 bg-white">
      <div class="flex items-center justify-between px-4 py-2 border-b border-slate-100">
        <h3 class="text-sm font-semibold">{TYPE_LABEL[group.type]}</h3>
        <span class="text-sm text-slate-600">{formatCurrency(group.subtotal)}</span>
      </div>
      <table class="w-full text-sm">
        <tbody>
          {#each group.rows as a (a.id)}
            <tr class="border-t border-slate-50">
              <td class="px-4 py-2">{a.name}</td>
              <td class="px-4 py-2 text-slate-500">{a.institution ?? ""}</td>
              <td class="px-4 py-2 text-right">
                {formatCurrency(a.balance_current, a.currency)}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/each}
</div>
