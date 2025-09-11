import { useState } from 'react';
import { addPosition } from '../lib/api';
function strategyActions(strategy) {
  if (!strategy) return '';
  const labels = String(strategy)
    .split('/')
    .map(s => s.trim())
    .map(s => s.replace(/\s+/g, '')); // 공백 제거해 라벨 표준화
  const actions = [];
  
  // 백엔드의 새로운 사용자 친화적 전략 용어와 매칭
  if (labels.includes('상승신호')) {
    actions.push('돌파하면 매수, DEMA10 아래로 마감하면 정리');
  }
  if (labels.includes('상승시작')) {
    actions.push('전일 고가 돌파 시 진입, MACD가 0선 아래면 비중 줄이기');
  }
  if (labels.includes('관심증가')) {
    actions.push('거래가 5일평균↑이면 비중 늘리기, 다음 날 거래 줄면 일부 청산');
  }
  if (labels.includes('상승추세정착')) {
    actions.push('추세 지속 시 비중 유지, 추세 전환 시 정리');
  }
  if (labels.includes('관심') || actions.length === 0) {
    actions.push('아직 기다리기 (신호 2개 이상 뜨면 진입)');
  }
  
  // 기존 용어도 호환성을 위해 유지
  if (labels.includes('골든크로스형성')) {
    actions.push('돌파하면 매수, DEMA10 아래로 마감하면 정리');
  }
  if (labels.includes('모멘텀양전환')) {
    actions.push('전일 고가 돌파 시 진입, MACD가 0선 아래면 비중 줄이기');
  }
  if (labels.includes('거래확대')) {
    actions.push('거래가 5일평균↑이면 비중 늘리기, 다음 날 거래 줄면 일부 청산');
  }
  if (labels.includes('관망')) {
    actions.push('아직 기다리기 (신호 2개 이상 뜨면 진입)');
  }
  
  return actions.join(' · ');
}

function labelMeta(label) {
  const v = String(label || '').trim();
  if (v === '강한 매수') {
    return {
      text: '매수 후보(강)',
      hint: '신호 충족도 높음. 전일 고가 돌파 시 분할 진입 고려, DEMA10 하회 시 정리.',
      cls: 'bg-emerald-100 text-emerald-800',
    };
  }
  if (v === '관심') {
    return {
      text: '관망/관찰',
      hint: '신호 일부 충족. 거래확대·모멘텀 확인 후 진입 판단.',
      cls: 'bg-amber-100 text-amber-800',
    };
  }
  return {
    text: '제외',
    hint: '조건 미충족. 대기.',
    cls: 'bg-slate-100 text-slate-700',
  };
}

export default function ResultTable({ items, showDetails=false }) {
  const [openDetail, setOpenDetail] = useState(null);
  const [openLabel, setOpenLabel] = useState(null);
  const [addingPosition, setAddingPosition] = useState(null);
  const [positionForm, setPositionForm] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    quantity: '10'
  });

  const handleAddPosition = async (ticker, name, score, strategy) => {
    if (!positionForm.quantity) {
      alert('수량을 입력해주세요.');
      return;
    }

    try {
      const result = await addPosition({
        ticker,
        entry_date: positionForm.entry_date,
        quantity: parseInt(positionForm.quantity),
        score: score,
        strategy: strategy
      });
      
      if (result.ok) {
        alert(`${name} 포지션이 추가되었습니다.`);
        setAddingPosition(null);
        setPositionForm({
          entry_date: new Date().toISOString().split('T')[0],
          quantity: '10'
        });
      } else {
        alert('포지션 추가 실패: ' + result.error);
      }
    } catch (e) {
      alert('포지션 추가 오류: ' + String(e));
    }
  };

  if (!items || !items.length) return <div className="text-sm text-gray-500">결과 없음</div>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white shadow rounded">
        <thead className="bg-gray-100 text-sm">
          <tr>
            <th className="p-2 text-left">이름(코드)</th>
            <th className="p-2 text-left">점수</th>
            <th className="p-2 text-left">평가</th>
            <th className="p-2 text-left">종가</th>
            <th className="p-2 text-left">전략</th>
            <th className="p-2 text-left">액션</th>
            <th className="p-2 text-left">포지션</th>
            <th className="p-2 text-left">상세</th>
          </tr>
        </thead>
        <tbody className="text-sm">
          {items.map((it) => (
            <tr key={it.ticker} className="border-t">
              <td className="p-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span>{it.name}</span>
                  <span className="font-mono text-xs text-gray-500">({it.ticker})</span>
                  {it.details?.recurrence?.appeared_before ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-violet-100 text-violet-800">
                      재등장 ×{it.details.recurrence.appear_count}
                    </span>
                  ) : (
                    it.details?.recurrence ? (
                      <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                        신규
                      </span>
                    ) : null
                  )}
                  {it.details?.recurrence?.first_as_of ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-100 text-sky-800">
                      첫등장 {it.details.recurrence.first_as_of}
                    </span>
                  ) : null}
                </div>
              </td>
              <td className="p-2">{(it.score ?? 0).toFixed(0)}</td>
              <td className="p-2 relative">
                {(() => {
                  const meta = labelMeta(it.score_label);
                  return (
                    <div className="inline-flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded ${meta.cls}`}>{meta.text}</span>
                      <button
                        className="text-[10px] w-4 h-4 rounded-full border text-slate-600 hover:bg-slate-100"
                        title="설명"
                        onClick={() => setOpenLabel(openLabel === it.ticker ? null : it.ticker)}
                      >i</button>
                      {openLabel === it.ticker && (
                        <div className="absolute z-10 mt-2 left-0 w-[280px] bg-white border rounded shadow p-2 text-xs">
                          {meta.hint}
                          <div className="text-right mt-2">
                            <button className="px-2 py-1 border rounded" onClick={() => setOpenLabel(null)}>닫기</button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </td>
              <td className="p-2">{it.details?.close ? Number(it.details.close).toLocaleString() : '-'}</td>
              <td className="p-2">{it.strategy}</td>
              <td className="p-2 text-gray-700">{strategyActions(it.strategy)}</td>
              <td className="p-2">
                <button
                  className="px-2 py-1 text-xs rounded bg-green-100 text-green-800 hover:bg-green-200 border"
                  onClick={() => {
                    setAddingPosition(it.ticker);
                    setPositionForm({
                      entry_date: new Date().toISOString().split('T')[0],
                      quantity: '10'
                    });
                  }}
                >
                  포지션 추가
                </button>
              </td>
              <td className="p-2 relative">
                {showDetails && (
                  <>
                    <button
                      className="px-2 py-1 text-xs rounded bg-slate-100 hover:bg-slate-200 border"
                      onClick={() => setOpenDetail(openDetail === it.ticker ? null : it.ticker)}
                    >
                      상세
                    </button>
                    {openDetail === it.ticker && (
                      <div className="absolute z-20 mt-2 right-0 w-[640px] max-w-[95vw] max-h-[70vh] overflow-y-auto bg-white border rounded shadow-xl p-3 text-xs">
                        <div className="font-semibold mb-1">상세 지표/조건</div>
                        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                          <div>match</div><div>{it.match ? '✅' : '—'}</div>
                          <div>cross</div><div>{it.flags?.details?.cross?.ok ? '✅' : '❌'}</div>
                          <div>volume</div><div>{it.flags?.details?.volume?.ok ? '✅' : '❌'}</div>
                          <div>macd</div><div>{it.flags?.details?.macd?.ok ? '✅' : '❌'}</div>
                          <div>rsi</div><div>{it.flags?.details?.rsi?.ok ? '✅' : '❌'}</div>
                          <div>tema_slope</div><div>{it.flags?.details?.tema_slope?.ok ? '✅' : '❌'}</div>
                          <div>obv_slope</div><div>{it.flags?.details?.obv_slope?.ok ? '✅' : '❌'}</div>
                          <div>above_cnt5</div><div>{it.flags?.details?.above_cnt5?.ok ? '✅' : '❌'}</div>
                        </div>
                        <div className="border-t my-2" />
                        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                          <div>TEMA-DEMA</div><div>{(it.indicators.TEMA - it.indicators.DEMA).toFixed(2)}</div>
                          <div>MACD_OSC</div><div>{it.indicators.MACD_OSC.toFixed(2)}</div>
                          <div>RSI</div><div>{it.indicators.RSI.toFixed(1)}</div>
                          <div>RSI_TEMA</div><div>{it.indicators.RSI_TEMA.toFixed(1)}</div>
                          <div>RSI_DEMA</div><div>{it.indicators.RSI_DEMA.toFixed(1)}</div>
                          <div>VOL</div><div>{it.indicators.VOL.toLocaleString()}</div>
                          <div>VOL_MA5</div><div>{it.indicators.VOL_MA5.toLocaleString()}</div>
                        </div>
                        <div className="border-t my-2" />
                        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                          <div>TEMA20_slope20</div><div>{it.trend ? it.trend.TEMA20_SLOPE20.toFixed(2) : '-'}</div>
                          <div>OBV_slope20</div><div>{it.trend ? it.trend.OBV_SLOPE20.toFixed(2) : '-'}</div>
                          <div>AboveCnt5</div><div>{it.trend ? it.trend.ABOVE_CNT5 : '-'}</div>
                        </div>
                        <div className="text-right mt-2">
                          <button className="px-2 py-1 border rounded" onClick={() => setOpenDetail(null)}>닫기</button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* 포지션 추가 모달 */}
      {addingPosition && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded shadow-lg w-96">
            <h3 className="text-lg font-semibold mb-4">포지션 추가</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">종목</label>
                <div className="text-sm text-gray-600">
                  {items.find(it => it.ticker === addingPosition)?.name} ({addingPosition})
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">진입일</label>
                <input
                  type="date"
                  className="w-full border rounded px-3 py-2"
                  value={positionForm.entry_date}
                  onChange={(e) => setPositionForm({...positionForm, entry_date: e.target.value})}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">수량</label>
                <input
                  type="number"
                  className="w-full border rounded px-3 py-2"
                  placeholder="수량"
                  value={positionForm.quantity}
                  onChange={(e) => setPositionForm({...positionForm, quantity: e.target.value})}
                />
              </div>
            </div>
            <div className="mt-6 flex gap-2">
              <button
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                onClick={() => {
                  const item = items.find(it => it.ticker === addingPosition);
                  handleAddPosition(addingPosition, item?.name, item?.score, item?.strategy);
                }}
              >
                추가
              </button>
              <button
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                onClick={() => {
                  setAddingPosition(null);
                  setPositionForm({
                    entry_date: new Date().toISOString().split('T')[0],
                    quantity: '10'
                  });
                }}
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


