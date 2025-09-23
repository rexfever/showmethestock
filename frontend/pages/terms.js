import Head from 'next/head';
import Link from 'next/link';

export default function Terms() {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <Head>
        <title>이용약관 - 스톡인사이트</title>
      </Head>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg p-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">이용약관</h1>
            <p className="text-gray-600">최종 수정일: 2024년 1월 1일</p>
          </div>

          <div className="prose prose-lg max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제1조 (목적)</h2>
              <p className="text-gray-700 leading-relaxed">
                본 약관은 스톡인사이트(이하 "서비스")가 제공하는 AI 기반 주식 분석 서비스의 이용과 관련하여 
                서비스 제공자와 이용자 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제2조 (정의)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. "서비스"란 AI 기술을 활용한 주식 시장 분석 및 투자 정보 제공 서비스를 의미합니다.</p>
                <p>2. "이용자"란 서비스에 접속하여 본 약관에 따라 서비스를 이용하는 회원을 의미합니다.</p>
                <p>3. "회원"이란 서비스에 개인정보를 제공하여 회원등록을 한 자로서, 서비스의 정보를 지속적으로 제공받으며 서비스를 계속적으로 이용할 수 있는 자를 의미합니다.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제3조 (약관의 효력 및 변경)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 본 약관은 서비스 화면에 게시하거나 기타의 방법으로 회원에게 공지함으로써 효력이 발생합니다.</p>
                <p>2. 서비스는 합리적인 사유가 발생할 경우에는 본 약관을 변경할 수 있으며, 약관이 변경되는 경우 변경된 약관의 내용과 시행일을 정하여, 시행일로부터 최소 7일 이전에 공지합니다.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제4조 (서비스의 제공)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 서비스는 다음과 같은 업무를 수행합니다:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>AI 기반 주식 시장 분석</li>
                  <li>투자 기회 알림 서비스</li>
                  <li>주식 관련 정보 제공</li>
                  <li>기타 서비스와 관련된 업무</li>
                </ul>
                <p>2. 서비스는 연중무휴, 1일 24시간 제공함을 원칙으로 합니다.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제5조 (서비스 이용의 제한)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>이용자는 다음 행위를 하여서는 안 됩니다:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>신청 또는 변경시 허위 내용의 등록</li>
                  <li>타인의 정보 도용</li>
                  <li>서비스에 게시된 정보의 변경</li>
                  <li>서비스가 정한 정보 이외의 정보(컴퓨터 프로그램 등) 등의 송신 또는 게시</li>
                  <li>서비스 기타 제3자의 저작권 등 지적재산권에 대한 침해</li>
                  <li>서비스 기타 제3자의 명예를 손상시키거나 업무를 방해하는 행위</li>
                </ul>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제6조 (면책조항)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 서비스는 천재지변 또는 이에 준하는 불가항력으로 인하여 서비스를 제공할 수 없는 경우에는 서비스 제공에 관한 책임이 면제됩니다.</p>
                <p>2. 서비스는 이용자의 귀책사유로 인한 서비스 이용의 장애에 대하여는 책임을 지지 않습니다.</p>
                <p>3. 서비스는 이용자가 서비스를 이용하여 기대하는 수익을 상실한 것에 대하여 책임을 지지 않으며 그 밖에 서비스를 통하여 얻은 자료로 인한 손해에 관하여는 책임을 지지 않습니다.</p>
                <p>4. 서비스에서 제공하는 정보는 투자 참고용이며, 투자 결정에 대한 책임은 이용자에게 있습니다.</p>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">제7조 (준거법 및 관할법원)</h2>
              <div className="text-gray-700 leading-relaxed space-y-2">
                <p>1. 서비스 이용과 관련하여 서비스와 이용자 간에 발생한 분쟁에 관한 소송은 민사소송법상의 관할법원에 제기합니다.</p>
                <p>2. 서비스 이용으로 발생한 분쟁에 대해 소송이 제기되는 경우 서비스의 본사 소재지를 관할하는 법원을 전속 관할법원으로 합니다.</p>
              </div>
            </section>
          </div>

          <div className="mt-12 pt-8 border-t border-gray-200">
            <div className="flex justify-center">
              <Link href="/signup" className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-md transition duration-200 inline-block">
                가입하기
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
