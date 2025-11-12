#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이메일 발송 모듈
Gmail SMTP를 사용하여 PDF 첨부 이메일 발송
"""
import os
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class EmailSender:
    """Gmail SMTP를 사용한 이메일 발송 클래스"""

    def __init__(self):
        self.gmail_email = os.getenv('GMAIL_SENDER_EMAIL')
        self.gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587

        if not self.gmail_email or not self.gmail_password:
            print("경고: Gmail 설정이 .env 파일에 없습니다")
        else:
            print(f"✓ Gmail SMTP 설정 완료: {self.gmail_email}")

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
        if not self.gmail_email or not self.gmail_password:
            print("[시뮬레이션] 이메일 발송:")
            print(f"  수신: {to_email}")
            print(f"  파일: {pdf_path}")
            print(f"  오류: {errors_count}개")
            return True

        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['From'] = f"PDF 맞춤법 검사기 <{self.gmail_email}>"
            msg['To'] = to_email
            msg['Subject'] = "[PDF 맞춤법 검사 완료] 결과를 확인하세요"

            # HTML 본문
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

            # 텍스트와 HTML 본문 추가
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

            # PDF 첨부 파일 추가
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()

            attachment = MIMEBase('application', 'pdf')
            attachment.set_payload(pdf_content)
            encoders.encode_base64(attachment)

            filename = f"{os.path.splitext(original_filename)[0]}_검사완료.pdf"
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename*=UTF-8\'\'{filename}'
            )
            msg.attach(attachment)

            # SMTP 서버 연결 및 이메일 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # TLS 암호화
                server.login(self.gmail_email, self.gmail_password)
                server.send_message(msg)

            print(f"✓ 이메일 발송 완료: {to_email}")
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
        if not self.gmail_email or not self.gmail_password:
            print(f"[시뮬레이션] 오류 알림 발송: {to_email}")
            return True

        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['From'] = f"PDF 맞춤법 검사기 <{self.gmail_email}>"
            msg['To'] = to_email
            msg['Subject'] = "[PDF 맞춤법 검사] 처리 중 오류 발생"

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

            # 텍스트와 HTML 본문 추가
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

            # SMTP 서버 연결 및 이메일 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_email, self.gmail_password)
                server.send_message(msg)

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
