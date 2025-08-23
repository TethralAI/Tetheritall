"""
Email Provider

Handles email notifications via SMTP.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from .base import BaseNotificationProvider
from ..models import Notification, NotificationTarget, DeliveryResult, DeliveryStatus, Platform

logger = logging.getLogger(__name__)


class EmailProvider(BaseNotificationProvider):
    """Email notification provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_username = config.get("smtp_username")
        self.smtp_password = config.get("smtp_password")
        self.use_tls = config.get("use_tls", True)
        self.from_email = config.get("from_email", "noreply@tetheritall.com")
        self.from_name = config.get("from_name", "Tetheritall IoT System")
        
        if not all([self.smtp_host, self.smtp_username, self.smtp_password]):
            logger.error("Email SMTP configuration incomplete")
            self.enabled = False
            
    async def send_notification(
        self,
        notification: Notification,
        target: NotificationTarget
    ) -> DeliveryResult:
        """Send notification via email."""
        if not self.enabled:
            return self._create_failure_result(
                notification, target, "Email provider not enabled"
            )
            
        if not self.validate_target(target):
            return self._create_failure_result(
                notification, target, "Invalid email target"
            )
            
        try:
            # Build email message
            message = self._build_email_message(notification, target)
            
            # Send email
            await self._send_email(message, target.token)
            
            return self._create_success_result(
                notification, target, "Email notification sent successfully"
            )
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return self._create_failure_result(
                notification, target, f"Email send error: {str(e)}"
            )
            
    async def send_bulk_notifications(
        self,
        notification: Notification,
        targets: List[NotificationTarget]
    ) -> List[DeliveryResult]:
        """Send bulk notifications via email."""
        if not self.enabled:
            return [
                self._create_failure_result(notification, target, "Email provider not enabled")
                for target in targets
            ]
            
        # Filter valid email targets
        email_targets = [target for target in targets if self.validate_target(target)]
        
        if not email_targets:
            return [
                self._create_failure_result(notification, target, "Invalid email target")
                for target in targets
            ]
            
        # Send emails concurrently
        tasks = [
            self.send_notification(notification, target)
            for target in email_targets
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(self._create_failure_result(
                    notification, email_targets[i], f"Email bulk error: {str(result)}"
                ))
            else:
                final_results.append(result)
                
        return final_results
        
    def validate_target(self, target: NotificationTarget) -> bool:
        """Validate email target."""
        if target.platform != Platform.EMAIL or not target.token:
            return False
            
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, target.token))
        
    def _build_email_message(self, notification: Notification, target: NotificationTarget) -> MIMEMultipart:
        """Build email message."""
        message = MIMEMultipart("alternative")
        
        if notification.content:
            subject = notification.content.title
            
            # Build HTML content
            html_content = self._build_html_content(notification)
            
            # Build plain text content
            text_content = self._build_text_content(notification)
            
        else:
            subject = "Tetheritall Notification"
            html_content = "<p>Notification from Tetheritall IoT System</p>"
            text_content = "Notification from Tetheritall IoT System"
            
        # Set headers
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = target.token
        
        # Add content
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")
        
        message.attach(text_part)
        message.attach(html_part)
        
        return message
        
    def _build_html_content(self, notification: Notification) -> str:
        """Build HTML email content."""
        if not notification.content:
            return "<p>Notification from Tetheritall IoT System</p>"
            
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ color: #333; margin-bottom: 20px; }}
                .content {{ color: #666; line-height: 1.6; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 12px; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="header">{notification.content.title}</h2>
                <div class="content">
                    <p>{notification.content.body}</p>
        """
        
        # Add action buttons if available
        if notification.content.actions:
            html += "<div>"
            for action in notification.content.actions:
                html += f'<a href="#" class="button">{action.get("title", "Action")}</a>'
            html += "</div>"
            
        # Add metadata
        html += f"""
                    <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 4px;">
                        <strong>Notification Details:</strong><br>
                        Type: {notification.notification_type.value}<br>
                        Priority: {notification.priority.value}<br>
                        Time: {notification.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
                    </div>
                </div>
                <div class="footer">
                    This is an automated notification from your Tetheritall IoT System.<br>
                    If you no longer wish to receive these emails, please contact support.
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    def _build_text_content(self, notification: Notification) -> str:
        """Build plain text email content."""
        if not notification.content:
            return "Notification from Tetheritall IoT System"
            
        text = f"{notification.content.title}\n\n"
        text += f"{notification.content.body}\n\n"
        
        # Add metadata
        text += "---\n"
        text += f"Type: {notification.notification_type.value}\n"
        text += f"Priority: {notification.priority.value}\n"
        text += f"Time: {notification.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        text += "This is an automated notification from your Tetheritall IoT System.\n"
        text += "If you no longer wish to receive these emails, please contact support."
        
        return text
        
    async def _send_email(self, message: MIMEMultipart, to_email: str):
        """Send email via SMTP."""
        try:
            # Connect to SMTP server
            server = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.use_tls,
                timeout=self.timeout
            )
            
            await server.connect()
            
            # Login if credentials provided
            if self.smtp_username and self.smtp_password:
                await server.login(self.smtp_username, self.smtp_password)
                
            # Send email
            await server.send_message(message)
            
            # Disconnect
            await server.quit()
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise
            
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get email provider status."""
        status = await super().get_provider_status()
        status.update({
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "use_tls": self.use_tls,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "credentials_configured": bool(self.smtp_username and self.smtp_password)
        })
        return status
