import Head from 'next/head';
import Link from 'next/link';

export default function Privacy() {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <Head>
        <title>개인정보처리방침 - 스톡인사이트</title>
      </Head>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg p-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">개인정보처리방침</h1>
            <p className="text-gray-600">최종 수정일: 2024년 1월 1일</p>
          </div>

          <div className="prose prose-lg max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제1조 (개인정보의 처리목적)</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                스톡인사이트(이하 "서비스")는 다음의 목적을 위하여 개인정보를 처리합니다. 처리하고 있는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며, 이용 목적이 변경되는 경우에는 개인정보보호법 제18조에 따라 별도의 동의를 받는 등 필요한 조치를 이행할 예정입니다.
              </p>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 회원 가입 및 관리: 회원제 서비스 이용에 따른 본인확인, 개인 식별, 불량회원의 부정 이용 방지와 비인가 사용 방지, 가입 의사 확인, 연령확인, 만14세 미만 아동 개인정보 수집 시 법정 대리인 동의여부 확인, 분쟁 조정을 위한 기록 보존, 고지사항 전달</p>
                <p>2. 서비스 제공: AI 기반 주식 분석 서비스 제공, 맞춤형 투자 정보 제공, 알림 서비스 제공</p>
                <p>3. 고충처리: 민원인의 신원 확인, 민원사항 확인, 사실조사를 위한 연락·통지, 처리결과 통보</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제2조 (개인정보의 처리 및 보유기간)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 서비스는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보를 수집 시에 동의받은 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.</p>
                <p>2. 각각의 개인정보 처리 및 보유 기간은 다음과 같습니다:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>회원 정보: 회원 탈퇴 시까지</li>
                  <li>서비스 이용 기록: 3년</li>
                  <li>알림 서비스 기록: 1년</li>
                </ul>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제3조 (처리하는 개인정보의 항목)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>서비스는 다음의 개인정보 항목을 처리하고 있습니다:</p>
                <div className="ml-4">
                  <p className="font-medium">필수항목:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>이메일 주소</li>
                    <li>닉네임</li>
                    <li>소셜 로그인 제공자 정보</li>
                  </ul>
                  <p className="font-medium mt-4">선택항목:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>프로필 이미지</li>
                    <li>투자 경험 수준</li>
                    <li>관심 분야</li>
                  </ul>
                </div>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제4조 (개인정보의 제3자 제공)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 서비스는 개인정보를 제1조(개인정보의 처리목적)에서 명시한 범위 내에서만 처리하며, 정보주체의 동의, 법률의 특별한 규정 등 개인정보보호법 제17조 및 제18조에 해당하는 경우에만 개인정보를 제3자에게 제공합니다.</p>
                <p>2. 서비스는 다음과 같이 개인정보를 제3자에게 제공하고 있습니다:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>제공받는 자: 카카오, 네이버, 토스 (소셜 로그인 서비스 제공자)</li>
                  <li>제공하는 항목: 이메일, 닉네임, 프로필 이미지</li>
                  <li>제공받는 자의 이용목적: 소셜 로그인 서비스 제공</li>
                  <li>보유 및 이용기간: 회원 탈퇴 시까지</li>
                </ul>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제5조 (개인정보처리의 위탁)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 서비스는 원활한 개인정보 업무처리를 위하여 다음과 같이 개인정보 처리업무를 위탁하고 있습니다:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>위탁받는 자: AWS (Amazon Web Services)</li>
                  <li>위탁하는 업무의 내용: 서버 운영 및 데이터 저장</li>
                  <li>위탁받는 자: 카카오</li>
                  <li>위탁하는 업무의 내용: 알림 서비스 제공</li>
                </ul>
                <p>2. 서비스는 위탁계약 체결시 개인정보보호법 제26조에 따라 위탁업무 수행목적 외 개인정보 처리금지, 기술적·관리적 보호조치, 재위탁 제한, 수탁자에 대한 관리·감독, 손해배상 등에 관한 사항을 계약서 등 문서에 명시하고, 수탁자가 개인정보를 안전하게 처리하는지를 감독하고 있습니다.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제6조 (정보주체의 권리·의무 및 행사방법)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>정보주체는 서비스에 대해 언제든지 다음 각 호의 개인정보 보호 관련 권리를 행사할 수 있습니다:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>개인정보 처리현황 통지요구</li>
                  <li>개인정보 열람요구</li>
                  <li>개인정보 정정·삭제요구</li>
                  <li>개인정보 처리정지 요구</li>
                </ul>
                <p>권리 행사는 서비스에 대해 개인정보보호법 시행령 제41조제1항에 따라 서면, 전화, 전자우편, 모사전송(FAX) 등을 통하여 하실 수 있으며 서비스는 이에 대해 지체없이 조치하겠습니다.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제7조 (개인정보의 안전성 확보조치)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>서비스는 개인정보의 안전성 확보를 위해 다음과 같은 조치를 취하고 있습니다:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>관리적 조치: 내부관리계획 수립·시행, 정기적 직원 교육 등</li>
                  <li>기술적 조치: 개인정보처리시스템 등의 접근권한 관리, 접근통제시스템 설치, 개인정보의 암호화, 보안프로그램 설치</li>
                  <li>물리적 조치: 전산실, 자료보관실 등의 접근통제</li>
                </ul>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제8조 (개인정보 보호책임자)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>서비스는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 개인정보 처리와 관련한 정보주체의 불만처리 및 피해구제 등을 위하여 아래와 같이 개인정보 보호책임자를 지정하고 있습니다:</p>
                <div className="ml-4">
                  <p>개인정보 보호책임자</p>
                  <p>연락처: privacy@stockinsight.com</p>
                </div>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제9조 (개인정보처리방침의 변경)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>이 개인정보처리방침은 시행일로부터 적용되며, 법령 및 방침에 따른 변경내용의 추가, 삭제 및 정정이 있는 경우에는 변경사항의 시행 7일 전부터 공지사항을 통하여 고지할 것입니다.</p>
              </div>
            </section>
          </div>

          <div className="mt-12 pt-8 border-t border-gray-200">
            <div className="flex justify-center">
              <Link href="/signup">
                <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-md transition duration-200">
                  가입하기
                </button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
