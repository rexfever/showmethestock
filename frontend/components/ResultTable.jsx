export default function ResultTable({ items }) {
  if (!items || !items.length) return <div className="text-sm text-gray-500">결과 없음</div>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white shadow rounded">
        <thead className="bg-gray-100 text-sm">
          <tr>
            <th className="p-2 text-left">코드</th>
            <th className="p-2 text-left">이름</th>
            <th className="p-2 text-left">match</th>
            <th className="p-2 text-left">TEMA-DEMA</th>
            <th className="p-2 text-left">MACD_OSC</th>
            <th className="p-2 text-left">RSI</th>
            <th className="p-2 text-left">RSI_TEMA</th>
            <th className="p-2 text-left">RSI_DEMA</th>
            <th className="p-2 text-left">VOL</th>
            <th className="p-2 text-left">VOL_MA5</th>
            <th className="p-2 text-left">전략</th>
          </tr>
        </thead>
        <tbody className="text-sm">
          {items.map((it) => (
            <tr key={it.ticker} className="border-t">
              <td className="p-2 font-mono">{it.ticker}</td>
              <td className="p-2">{it.name}</td>
              <td className="p-2">{it.match ? '✅' : '—'}</td>
              <td className="p-2">{(it.indicators.TEMA - it.indicators.DEMA).toFixed(2)}</td>
              <td className="p-2">{it.indicators.MACD_OSC.toFixed(2)}</td>
              <td className="p-2">{it.indicators.RSI.toFixed(1)}</td>
              <td className="p-2">{it.indicators.RSI_TEMA.toFixed(1)}</td>
              <td className="p-2">{it.indicators.RSI_DEMA.toFixed(1)}</td>
              <td className="p-2">{it.indicators.VOL.toLocaleString()}</td>
              <td className="p-2">{it.indicators.VOL_MA5.toLocaleString()}</td>
              <td className="p-2">{it.strategy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


