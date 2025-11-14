export default function SEOContent() {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 space-y-6 text-gray-700">
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          PDF 한국어 맞춤법 검사기란?
        </h2>
        <p className="leading-relaxed">
          PDF 한국어 맞춤법 검사기는 PDF 문서의 한국어 맞춤법과 띄어쓰기를 자동으로 검사하여
          오류를 빨간색으로 표시해주는 무료 온라인 서비스입니다. 업로드한 PDF 파일을 분석하여
          맞춤법 오류를 찾아내고, 각 오류에 대한 수정 제안을 주석으로 추가하여 이메일로 전송해드립니다.
        </p>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          주요 기능
        </h2>
        <ul className="list-disc list-inside space-y-2">
          <li>PDF 파일 업로드 및 자동 맞춤법 검사</li>
          <li>맞춤법 오류를 빨간색으로 강조 표시</li>
          <li>각 오류에 대한 수정 제안 제공</li>
          <li>검사 완료된 PDF를 이메일로 전송</li>
          <li>최대 30MB 크기의 PDF 파일 지원</li>
          <li>완전 무료 서비스</li>
        </ul>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          사용 방법
        </h2>
        <ol className="list-decimal list-inside space-y-2">
          <li>검사하고 싶은 PDF 파일을 업로드합니다</li>
          <li>결과를 받을 이메일 주소를 입력합니다</li>
          <li>"맞춤법 검사하기" 버튼을 클릭합니다</li>
          <li>짧은 광고를 시청합니다 (15-30초)</li>
          <li>5분 이내에 이메일로 검사 완료된 PDF를 받습니다</li>
          <li>PDF를 열어 빨간색으로 표시된 오류를 확인하고 수정합니다</li>
        </ol>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          누가 사용하면 좋을까요?
        </h2>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>학생</strong>: 과제, 리포트, 논문 작성 시 맞춤법 검사</li>
          <li><strong>직장인</strong>: 업무 문서, 제안서, 보고서 교정</li>
          <li><strong>작가</strong>: 원고, 기고문 맞춤법 확인</li>
          <li><strong>연구자</strong>: 연구 논문, 학술 자료 교정</li>
          <li><strong>번역가</strong>: 번역 결과물 맞춤법 검증</li>
        </ul>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          왜 PDF 맞춤법 검사기를 사용해야 하나요?
        </h2>
        <div className="space-y-3">
          <p>
            <strong>정확성:</strong> 네이버와 부산대학교의 맞춤법 검사 API를 활용하여
            높은 정확도로 오류를 감지합니다.
          </p>
          <p>
            <strong>편리성:</strong> PDF 파일을 그대로 업로드하면 되므로 별도의 변환 작업이 필요 없습니다.
          </p>
          <p>
            <strong>시각적 표시:</strong> 오류를 빨간색으로 강조하여 한눈에 파악할 수 있습니다.
          </p>
          <p>
            <strong>수정 제안:</strong> 각 오류에 대한 올바른 표현을 제안하여 쉽게 수정할 수 있습니다.
          </p>
          <p>
            <strong>무료:</strong> 짧은 광고 시청만으로 완전 무료로 이용할 수 있습니다.
          </p>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          자주 묻는 질문 (FAQ)
        </h2>
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-lg text-gray-900">
              Q: 업로드한 PDF 파일은 안전하게 보관되나요?
            </h3>
            <p className="mt-2">
              A: 업로드된 파일은 검사 완료 후 즉시 서버에서 삭제됩니다.
              사용자의 개인정보와 파일은 저장되지 않으므로 안심하고 이용하실 수 있습니다.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-lg text-gray-900">
              Q: 검사 결과를 받는 데 얼마나 걸리나요?
            </h3>
            <p className="mt-2">
              A: 일반적으로 5분 이내에 이메일로 결과를 받으실 수 있습니다.
              파일 크기와 서버 상황에 따라 다소 시간이 걸릴 수 있습니다.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-lg text-gray-900">
              Q: 어떤 형식의 PDF 파일을 지원하나요?
            </h3>
            <p className="mt-2">
              A: 텍스트를 포함한 모든 PDF 파일을 지원합니다.
              단, 이미지로만 구성된 스캔 PDF는 텍스트 추출이 어려울 수 있습니다.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-lg text-gray-900">
              Q: 파일 크기 제한이 있나요?
            </h3>
            <p className="mt-2">
              A: 최대 30MB까지 업로드 가능합니다.
              대부분의 문서는 이 크기 내에서 처리 가능합니다.
            </p>
          </div>
        </div>
      </section>

      <section className="bg-blue-50 p-6 rounded-lg">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          지금 바로 시작하세요!
        </h2>
        <p className="leading-relaxed">
          완벽한 문서 작성을 위한 첫 걸음, PDF 한국어 맞춤법 검사기와 함께 시작하세요.
          간단한 업로드만으로 전문적인 맞춤법 검사를 경험하실 수 있습니다.
        </p>
      </section>
    </div>
  )
}
