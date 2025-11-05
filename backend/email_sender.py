#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이메일 발송 모듈
Resend API를 사용하여 PDF 첨부 이메일 발송
"""
import os
import base64
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Resend 라이브러리 import (설치된 경우)
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    print("경고: resend 라이브러리가 설치되지 않았습니다")


class EmailSender:
    """Resend API를 사용한 이메일 발송 클래스"""

    def __init__(self):
        if RESEND_AVAILABLE:
            api_key = os.getenv('RESEND_API_KEY')
            print(f"DEBUG: RESEND_API_KEY = {api_key[:10] if api_key else 'None'}...")
            resend.api_key = api_key
        self.from_email = os.getenv(
            'RESEND_FROM_EMAIL',
            'noreply@pdfgrammercheckorean.site'
        )
        print(f"DEBUG: FROM_EMAIL = {self.from_email}")

    def send_grammar_check_result(
        self,
        to_email: str,
        pdf_path: str,
        errors_count: int,
        original_filename: str
    ) -> bool:
        """
        맞춤법 검사 결과 이메일 발송

        Args:
            to_email: 수신자 이메일
            pdf_path: 첨부할 PDF 파일 경로
            errors_count: 발견된 오류 개수
            original_filename: 원본 파일명

        Returns:
            bool: 발송 성공 여부
        """
        if not RESEND_AVAILABLE:
            print("[시뮬레이션] 이메일 발송:")
            print(f"  수신: {to_email}")
            print(f"  파일: {pdf_path}")
            print(f"  오류: {errors_count}개")
            return True

        try:
            # PDF 파일 읽기
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
                pdf_base64 = base64.b64encode(pdf_content).decode()

            # 이메일 내용 구성
            subject = "[PDF 맞춤법 검사 완료] 결과를 확인하세요"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">PDF 맞춤법 검사 완료</h2>

                    <p>안녕하세요,</p>

                    <p>요청하신 <strong>{original_filename}</strong> 파일의 맞춤법 검사가 완료되었습니다.</p>

                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #495057;">검사 결과</h3>
                        <p style="margin: 10px 0;">
                            <strong>총 오류 개수:</strong> <span style="color: #dc3545; font-size: 18px;">{errors_count}개</span>
                        </p>
                        <p style="margin: 10px 0;">
                            첨부된 PDF 파일에 빨간색으로 표시되어 있습니다.
                        </p>
                    </div>

                    <p><strong>사용 방법:</strong></p>
                    <ol>
                        <li>첨부된 PDF 파일을 다운로드하세요</li>
                        <li>PDF 뷰어로 파일을 열어주세요</li>
                        <li>빨간색 주석을 클릭하면 수정 제안을 확인할 수 있습니다</li>
                    </ol>

                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">

                    <p style="font-size: 14px; color: #6c757d;">
                        감사합니다.<br>
                        <strong>PDF 한국어 맞춤법 검사기</strong>
                    </p>

                    <p style="font-size: 12px; color: #adb5bd; margin-top: 20px;">
                        이 이메일은 <a href="https://pdfgrammercheckorean.site" style="color: #007bff;">pdfgrammercheckorean.site</a>에서 발송되었습니다.
                    </p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
안녕하세요,

요청하신 PDF 맞춤법 검사가 완료되었습니다.

검사 결과:
- 파일명: {original_filename}
- 총 오류 개수: {errors_count}개
- 첨부된 PDF에 빨간색으로 표시되어 있습니다.

주석을 클릭하시면 수정 제안을 확인하실 수 있습니다.

감사합니다.
PDF 한국어 맞춤법 검사기
            """

            # Resend API로 이메일 발송
            response = resend.Emails.send({
                "from": self.from_email,
                "to": to_email,
                "subject": subject,
                "html": html_body,
                "text": text_body,
                "attachments": [
                    {
                        "filename": f"{os.path.splitext(original_filename)[0]}_검사완료.pdf",
                        "content": pdf_base64
                    }
                ]
            })

            print(f"✓ 이메일 발송 완료: {to_email}")
            print(f"  Resend ID: {response.get('id', 'N/A')}")
            return True

        except Exception as e:
            print(f"✗ 이메일 발송 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_error_notification(self, to_email: str, error_message: str) -> bool:
        """
        오류 발생 알림 이메일 발송

        Args:
            to_email: 수신자 이메일
            error_message: 오류 메시지

        Returns:
            bool: 발송 성공 여부
        """
        if not RESEND_AVAILABLE:
            print(f"[시뮬레이션] 오류 알림 발송: {to_email}")
            return True

        try:
            subject = "[PDF 맞춤법 검사] 처리 중 오류 발생"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #dc3545;">처리 중 오류 발생</h2>

                    <p>안녕하세요,</p>

                    <p>요청하신 PDF 파일 처리 중 오류가 발생했습니다.</p>

                    <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
                        <p style="margin: 0; color: #721c24;">
                            <strong>오류 내용:</strong> {error_message}
                        </p>
                    </div>

                    <p>다시 시도해주시거나, 문제가 지속되면 다른 PDF 파일로 시도해주세요.</p>

                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">

                    <p style="font-size: 14px; color: #6c757d;">
                        문의사항이 있으시면 언제든 연락주세요.<br>
                        <strong>PDF 한국어 맞춤법 검사기</strong>
                    </p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
안녕하세요,

요청하신 PDF 파일 처리 중 오류가 발생했습니다.

오류 내용: {error_message}

다시 시도해주시거나, 문제가 지속되면 다른 PDF 파일로 시도해주세요.

감사합니다.
PDF 한국어 맞춤법 검사기
            """

            response = resend.Emails.send({
                "from": self.from_email,
                "to": to_email,
                "subject": subject,
                "html": html_body,
                "text": text_body
            })

            print(f"✓ 오류 알림 발송 완료: {to_email}")
            return True

        except Exception as e:
            print(f"✗ 오류 알림 발송 실패: {e}")
            return False


# 테스트
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("사용법: python email_sender.py <수신_이메일> <PDF_경로> <오류_개수> [원본_파일명]")
        sys.exit(1)

    to_email = sys.argv[1]
    pdf_path = sys.argv[2]
    errors_count = int(sys.argv[3])
    original_filename = sys.argv[4] if len(sys.argv) > 4 else "test.pdf"

    print("=" * 60)
    print("이메일 발송 테스트")
    print("=" * 60)
    print(f"수신: {to_email}")
    print(f"파일: {pdf_path}")
    print(f"오류: {errors_count}개")
    print("=" * 60 + "\n")

    sender = EmailSender()
    success = sender.send_grammar_check_result(
        to_email, pdf_path, errors_count, original_filename
    )

    if success:
        print("\n✓ 발송 완료!")
    else:
        print("\n✗ 발송 실패!")
