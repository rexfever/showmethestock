/**
 * Scanner V3 전용 장세 카드 컴포넌트
 * v3 케이스(1/2/3/4)에 따라 사용자 친화적인 문구를 표시합니다.
 * 기술 용어를 제거하고, 투자 경험이 없는 사용자도 이해할 수 있는 표현만 사용합니다.
 */
export default function V3MarketRegimeCard({ v3CaseInfo }) {
  if (!v3CaseInfo) {
    return null;
  }

  const { has_recommendations, active_engines, engine_labels } = v3CaseInfo;
  
  // 케이스 판별
  const hasV2Lite = active_engines.includes("v2lite");
  const hasMidterm = active_engines.includes("midterm");
  
  let caseType = '4'; // 기본값: 둘 다 없음
  if (hasV2Lite && hasMidterm) {
    caseType = '1'; // CASE 1: v2-lite & midterm 모두
  } else if (hasMidterm && !hasV2Lite) {
    caseType = '2'; // CASE 2: midterm만
  } else if (hasV2Lite && !hasMidterm) {
    caseType = '3'; // CASE 3: v2-lite만
  }
  
  // 케이스별 문구 설정 (사용자 친화적 표현, 기술 용어 제거)
  // [시간축 컨텍스트 통일] "오늘은", "하루 안", "당장" 등 장중 표현 금지
  const caseConfig = {
    '1': {
      title: "📈 흐름이 이어질 가능성이 있는 종목이 있습니다",
      lines: [
        "며칠 이상 이어질 수 있는 흐름을 기준으로 종목을 골랐습니다.",
        "다음 거래일에 가격이 흔들릴 수 있지만, 전체 방향이 더 중요합니다.",
        "즉시 결정하지 않아도, 추세가 유지되는지 지켜보는 전략이 적합합니다."
      ],
      bgColor: "bg-blue-50",
      borderColor: "border-blue-200",
      textColor: "text-blue-800"
    },
    '2': {
      title: "📊 천천히 이어지는 흐름을 보는 날입니다",
      lines: [
        "단기적인 변동보다, 며칠 이상 이어질 가능성을 기준으로 선별했습니다.",
        "다음 거래일의 움직임에 즉시 반응할 필요는 없습니다.",
        "중간에 흔들림이 있어도 흐름이 유지되는지가 핵심입니다."
      ],
      bgColor: "bg-green-50",
      borderColor: "border-green-200",
      textColor: "text-green-800"
    },
    '3': {
      title: "⏱ 다음 거래일에 판단이 필요한 날입니다",
      lines: [
        "다음 거래일에 가격 변동이 커질 수 있습니다.",
        "신호가 자주 나오지 않도록 제한적으로 선별되었습니다.",
        "무리한 진입보다는 가볍게 관찰하거나 소액 대응이 적합합니다."
      ],
      bgColor: "bg-purple-50",
      borderColor: "border-purple-200",
      textColor: "text-purple-800"
    },
    '4': {
      title: "☕ 굳이 판단하지 않아도 됩니다",
      lines: [
        "뚜렷한 방향이 보이지 않는 상태입니다.",
        "움직이지 않는 것이 더 유리할 수 있습니다.",
        "다음 기회를 기다려도 늦지 않습니다."
      ],
      bgColor: "bg-gray-50",
      borderColor: "border-gray-200",
      textColor: "text-gray-800"
    }
  };
  
  const config = caseConfig[caseType];
  
  return (
    <div className={`${config.bgColor} border ${config.borderColor} rounded-lg p-4 mb-4`}>
      <div className="mb-3">
        <h3 className={`text-lg font-semibold ${config.textColor}`}>
          {config.title}
        </h3>
      </div>
      
      <div className="space-y-2">
        {config.lines.map((line, index) => (
          <p key={index} className={`text-sm ${config.textColor} leading-relaxed`}>
            - {line}
          </p>
        ))}
      </div>
    </div>
  );
}
