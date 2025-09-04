export default function ValidateTable({ items }) {
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) return <div className="text-sm text-gray-500">결과 없음</div>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white shadow rounded">
        <thead className="bg-gray-100 text-sm">
          <tr>
            <th className="p-2 text-left">코드</th>
            <th className="p-2 text-left">이름</th>
            <th className="p-2 text-left">점수(당시)</th>
            <th className="p-2 text-left">전략(당시)</th>
            <th className="p-2 text-left">현재 수익률(%)</th>
            <th className="p-2 text-left">기간내 최대 수익률(%)</th>
          </tr>
        </thead>
        <tbody className="text-sm">
          {rows.map((r) => (
            <tr key={r.ticker} className="border-t">
              <td className="p-2 font-mono">{r.ticker}</td>
              <td className="p-2">{r.name}</td>
              <td className="p-2">{r.score_then != null ? Number(r.score_then).toFixed(0) : '-'}</td>
              <td className="p-2">{r.strategy_then || '-'}</td>
              <td className="p-2">{Number(r.return_pct ?? 0).toFixed(2)}</td>
              <td className="p-2">{Number(r.max_return_pct ?? 0).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


