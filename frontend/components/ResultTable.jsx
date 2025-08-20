function strategyActions(strategy) {
  if (!strategy) return '';
  const labels = String(strategy)
    .split('/')
    .map(s => s.trim())
    .map(s => s.replace(/\s+/g, '')); // 공백 제거해 라벨 표준화
  const actions = [];
  if (labels.includes('골든크로스형성')) {
    actions.push('돌파하면 매수, DEMA10 아래로 마감하면 정리');
  }
  if (labels.includes('모멘텀양전환')) {
    actions.push('전일 고가 돌파 시 진입, MACD가 0선 아래면 비중 줄이기');
  }
  if (labels.includes('거래확대')) {
    actions.push('거래가 5일평균↑이면 비중 늘리기, 다음 날 거래 줄면 일부 청산');
  }
  if (labels.includes('관망') || actions.length === 0) {
    actions.push('아직 기다리기 (신호 2개 이상 뜨면 진입)');
  }
  return actions.join(' · ');
}

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
            <th className="p-2 text-left">점수</th>
            <th className="p-2 text-left">평가</th>
            <th className="p-2 text-left">cross</th>
            <th className="p-2 text-left">volume</th>
            <th className="p-2 text-left">macd</th>
            <th className="p-2 text-left">rsi</th>
            <th className="p-2 text-left">tema_slope</th>
            <th className="p-2 text-left">obv_slope</th>
            <th className="p-2 text-left">above_cnt5</th>
            <th className="p-2 text-left">TEMA-DEMA</th>
            <th className="p-2 text-left">MACD_OSC</th>
            <th className="p-2 text-left">RSI</th>
            <th className="p-2 text-left">RSI_TEMA</th>
            <th className="p-2 text-left">RSI_DEMA</th>
            <th className="p-2 text-left">VOL</th>
            <th className="p-2 text-left">VOL_MA5</th>
            <th className="p-2 text-left">전략</th>
            <th className="p-2 text-left">TEMA20_slope20</th>
            <th className="p-2 text-left">OBV_slope20</th>
            <th className="p-2 text-left">AboveCnt5</th>
            <th className="p-2 text-left">액션</th>
          </tr>
        </thead>
        <tbody className="text-sm">
          {items.map((it) => (
            <tr key={it.ticker} className="border-t">
              <td className="p-2 font-mono">{it.ticker}</td>
              <td className="p-2">{it.name}</td>
              <td className="p-2">{it.match ? '✅' : '—'}</td>
              <td className="p-2">{(it.score ?? 0).toFixed(0)}</td>
              <td className="p-2">{it.score_label || '-'}</td>
              <td className="p-2">{it.flags?.details?.cross?.ok ? '✅' : '❌'}</td>
              <td className="p-2">{it.flags?.details?.volume?.ok ? '✅' : '❌'}</td>
              <td className="p-2">{it.flags?.details?.macd?.ok ? '✅' : '❌'}</td>
              <td className="p-2">{it.flags?.details?.rsi?.ok ? '✅' : '❌'}</td>
              <td className="p-2">{it.flags?.details?.tema_slope?.ok ? '✅' : '❌'}</td>
              <td className="p-2">{it.flags?.details?.obv_slope?.ok ? '✅' : '❌'}</td>
              <td className="p-2">{it.flags?.details?.above_cnt5?.ok ? '✅' : '❌'}</td>
              <td className="p-2">{(it.indicators.TEMA - it.indicators.DEMA).toFixed(2)}</td>
              <td className="p-2">{it.indicators.MACD_OSC.toFixed(2)}</td>
              <td className="p-2">{it.indicators.RSI.toFixed(1)}</td>
              <td className="p-2">{it.indicators.RSI_TEMA.toFixed(1)}</td>
              <td className="p-2">{it.indicators.RSI_DEMA.toFixed(1)}</td>
              <td className="p-2">{it.indicators.VOL.toLocaleString()}</td>
              <td className="p-2">{it.indicators.VOL_MA5.toLocaleString()}</td>
              <td className="p-2">{it.strategy}</td>
              <td className="p-2">{it.trend ? it.trend.TEMA20_SLOPE20.toFixed(2) : '-'}</td>
              <td className="p-2">{it.trend ? it.trend.OBV_SLOPE20.toFixed(2) : '-'}</td>
              <td className="p-2">{it.trend ? it.trend.ABOVE_CNT5 : '-'}</td>
              <td className="p-2 text-gray-700">{strategyActions(it.strategy)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


