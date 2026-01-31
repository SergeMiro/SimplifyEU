"""
Email Service for sending subscription analysis reports.
Uses SMTP with HTML templates for professional email delivery.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Optional
import logging

from ..config import settings
from ..db.models import Analysis, AnalysisItem

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email reports via SMTP."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.sender_email = settings.SMTP_SENDER_EMAIL
        self.sender_name = settings.SMTP_SENDER_NAME
        self.use_tls = settings.SMTP_USE_TLS
        self.use_ssl = settings.SMTP_USE_SSL

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and return an SMTP connection."""
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port)
        else:
            server = smtplib.SMTP(self.host, self.port)
            if self.use_tls:
                server.starttls()
        
        server.login(self.user, self.password)
        return server

    def _generate_html_report(
        self,
        analysis: Analysis,
        items: list[AnalysisItem]
    ) -> str:
        """Generate HTML email body with analysis results."""
        subscriptions = [item for item in items if item.is_subscription]
        total_monthly = sum(item.amount_avg for item in subscriptions)
        
        # Build subscription rows
        subscription_rows = ""
        for item in subscriptions:
            frequency_label = {
                "monthly": "Ежемесячно",
                "weekly": "Еженедельно",
                "yearly": "Ежегодно",
                "quarterly": "Ежеквартально"
            }.get(item.frequency, item.frequency)
            
            merchant_display = item.merchant_name or item.merchant_descriptor
            subscription_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{merchant_display}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">{frequency_label}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: 600;">€{item.amount_avg:.2f}</td>
            </tr>
            """
        
        if not subscription_rows:
            subscription_rows = """
            <tr>
                <td colspan="3" style="padding: 24px; text-align: center; color: #6b7280;">
                    Подписок не обнаружено
                </td>
            </tr>
            """

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчёт об анализе подписок</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px 16px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">
                                📊 SimplifyEU
                            </h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 14px;">
                                Отчёт об анализе подписок
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Summary Cards -->
                    <tr>
                        <td style="padding: 24px;">
                            <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="width: 50%; padding: 8px;">
                                        <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 12px; padding: 20px; text-align: center;">
                                            <p style="margin: 0; font-size: 32px; font-weight: 700; color: #0369a1;">
                                                {len(subscriptions)}
                                            </p>
                                            <p style="margin: 4px 0 0 0; font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
                                                Подписок найдено
                                            </p>
                                        </div>
                                    </td>
                                    <td style="width: 50%; padding: 8px;">
                                        <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; padding: 20px; text-align: center;">
                                            <p style="margin: 0; font-size: 32px; font-weight: 700; color: #b45309;">
                                                €{total_monthly:.2f}
                                            </p>
                                            <p style="margin: 4px 0 0 0; font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">
                                                В месяц
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Analysis Details -->
                    <tr>
                        <td style="padding: 0 24px;">
                            <div style="background-color: #f9fafb; border-radius: 12px; padding: 16px;">
                                <table role="presentation" style="width: 100%;">
                                    <tr>
                                        <td style="font-size: 13px; color: #6b7280; padding: 4px 0;">
                                            <strong>ID анализа:</strong> {analysis.id}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="font-size: 13px; color: #6b7280; padding: 4px 0;">
                                            <strong>Файл:</strong> {analysis.filename}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="font-size: 13px; color: #6b7280; padding: 4px 0;">
                                            <strong>Транзакций обработано:</strong> {analysis.total_transactions or 0}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="font-size: 13px; color: #6b7280; padding: 4px 0;">
                                            <strong>Дата создания:</strong> {analysis.created_at.strftime('%d.%m.%Y %H:%M') if analysis.created_at else 'N/A'}
                                        </td>
                                    </tr>
                                </table>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Subscriptions Table -->
                    <tr>
                        <td style="padding: 24px;">
                            <h2 style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #1f2937;">
                                🔄 Обнаруженные подписки
                            </h2>
                            <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                                <thead>
                                    <tr style="background-color: #f9fafb;">
                                        <th style="padding: 12px; text-align: left; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase;">Сервис</th>
                                        <th style="padding: 12px; text-align: center; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase;">Периодичность</th>
                                        <th style="padding: 12px; text-align: right; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase;">Сумма</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {subscription_rows}
                                </tbody>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px; background-color: #f9fafb; border-radius: 0 0 16px 16px;">
                            <p style="margin: 0; font-size: 12px; color: #9ca3af; text-align: center;">
                                Этот отчёт был сгенерирован автоматически сервисом SimplifyEU.<br>
                                © {datetime.now().year} SimplifyEU. Все права защищены.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        return html

    def _generate_plain_text_report(
        self,
        analysis: Analysis,
        items: list[AnalysisItem]
    ) -> str:
        """Generate plain text email body for clients without HTML support."""
        subscriptions = [item for item in items if item.is_subscription]
        total_monthly = sum(item.amount_avg for item in subscriptions)
        
        lines = [
            "=" * 50,
            "SimplifyEU - Отчёт об анализе подписок",
            "=" * 50,
            "",
            f"ID анализа: {analysis.id}",
            f"Файл: {analysis.filename}",
            f"Транзакций обработано: {analysis.total_transactions or 0}",
            f"Подписок найдено: {len(subscriptions)}",
            f"Общая сумма в месяц: €{total_monthly:.2f}",
            "",
            "-" * 50,
            "Обнаруженные подписки:",
            "-" * 50,
        ]
        
        if subscriptions:
            for item in subscriptions:
                frequency_label = {
                    "monthly": "Ежемесячно",
                    "weekly": "Еженедельно",
                    "yearly": "Ежегодно",
                    "quarterly": "Ежеквартально"
                }.get(item.frequency, item.frequency)
                merchant_display = item.merchant_name or item.merchant_descriptor
                lines.append(f"• {merchant_display}: €{item.amount_avg:.2f} ({frequency_label})")
        else:
            lines.append("Подписок не обнаружено.")
        
        lines.extend([
            "",
            "=" * 50,
            f"© {datetime.now().year} SimplifyEU",
        ])
        
        return "\n".join(lines)

    async def send_report_email(
        self,
        recipient_email: str,
        analysis: Analysis,
        items: list[AnalysisItem],
        pdf_bytes: Optional[bytes] = None,
        recipient_name: Optional[str] = None
    ) -> dict:
        """
        Send analysis report via email.
        
        Args:
            recipient_email: Email address to send the report to
            analysis: Analysis object with report data
            items: List of AnalysisItem objects
            pdf_bytes: Optional PDF report attachment
            recipient_name: Optional recipient name for personalization
            
        Returns:
            dict with status and message
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"📊 Отчёт SimplifyEU: {len([i for i in items if i.is_subscription])} подписок найдено"
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = recipient_email
            
            # Generate content
            html_content = self._generate_html_report(analysis, items)
            text_content = self._generate_plain_text_report(analysis, items)
            
            # Attach parts
            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Attach PDF if provided
            if pdf_bytes:
                pdf_attachment = MIMEBase("application", "pdf")
                pdf_attachment.set_payload(pdf_bytes)
                encoders.encode_base64(pdf_attachment)
                pdf_attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=f"SimplifyEU_Report_{analysis.id}.pdf"
                )
                msg.attach(pdf_attachment)
            
            # Send email
            server = self._create_smtp_connection()
            try:
                server.sendmail(self.sender_email, recipient_email, msg.as_string())
                logger.info(f"Report email sent successfully to {recipient_email}")
                return {
                    "success": True,
                    "message": f"Report sent successfully to {recipient_email}"
                }
            finally:
                server.quit()
                
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return {
                "success": False,
                "message": "Email authentication failed. Please check SMTP credentials."
            }
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}"
            }

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured (not using placeholder values)."""
        return (
            self.host != "smtp.example.com" and
            self.user != "your_smtp_user@example.com" and
            self.password != "your_smtp_password"
        )


# Singleton instance
email_service = EmailService()
