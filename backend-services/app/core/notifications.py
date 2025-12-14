"""
Deployment notification service for Slack and email
"""

import aiohttp
import logging
import os
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send deployment notifications to Slack."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
    
    async def send_deployment_notification(
        self,
        environment: str,
        status: str,
        version: str,
        details: Optional[str] = None,
        deployment_time: Optional[float] = None
    ):
        """Send deployment notification to Slack."""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        color = "good" if status == "success" else "danger"
        deployment_time_str = f"{deployment_time:.2f}s" if deployment_time else "N/A"
        
        message = {
            "attachments": [
                {
                    "color": color,
                    "title": f"Deployment {status.upper()}",
                    "fields": [
                        {"title": "Environment", "value": environment, "short": True},
                        {"title": "Status", "value": status, "short": True},
                        {"title": "Version", "value": version, "short": True},
                        {"title": "Time", "value": deployment_time_str, "short": True},
                        {"title": "Timestamp", "value": datetime.now().isoformat(), "short": False},
                    ],
                    "footer": "Decentralized IoT Network",
                }
            ]
        }
        
        if details:
            message["attachments"][0]["fields"].append({
                "title": "Details",
                "value": details,
                "short": False
            })
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=message) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent for {environment} {status}")
                    else:
                        logger.error(f"Failed to send Slack notification: {response.status}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")


class EmailNotifier:
    """Send deployment notifications via email."""
    
    def __init__(self, smtp_server: Optional[str] = None, smtp_port: int = 587):
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER')
        self.smtp_port = smtp_port
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
    
    async def send_deployment_notification(
        self,
        recipient: str,
        environment: str,
        status: str,
        version: str,
        details: Optional[str] = None,
        deployment_time: Optional[float] = None
    ):
        """Send deployment notification via email."""
        if not all([self.smtp_server, self.sender_email, self.sender_password]):
            logger.warning("Email configuration incomplete")
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            deployment_time_str = f"{deployment_time:.2f}s" if deployment_time else "N/A"
            
            subject = f"Deployment {status.upper()}: {environment} v{version}"
            
            html_body = f"""
            <html>
              <body>
                <h2>Deployment Notification</h2>
                <table border="1" cellpadding="5">
                  <tr>
                    <td><strong>Environment</strong></td>
                    <td>{environment}</td>
                  </tr>
                  <tr>
                    <td><strong>Status</strong></td>
                    <td style="color: {'green' if status == 'success' else 'red'}">{status.upper()}</td>
                  </tr>
                  <tr>
                    <td><strong>Version</strong></td>
                    <td>{version}</td>
                  </tr>
                  <tr>
                    <td><strong>Deployment Time</strong></td>
                    <td>{deployment_time_str}</td>
                  </tr>
                  <tr>
                    <td><strong>Timestamp</strong></td>
                    <td>{datetime.now().isoformat()}</td>
                  </tr>
                </table>
                {f'<h3>Details</h3><p>{details}</p>' if details else ''}
              </body>
            </html>
            """
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient
            
            msg.attach(MIMEText(html_body, "html"))
            
            # Send via SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipient, msg.as_string())
            server.quit()
            
            logger.info(f"Email notification sent to {recipient}")
        
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")


class DeploymentNotifier:
    """Unified deployment notification service."""
    
    def __init__(self):
        self.slack = SlackNotifier()
        self.email = EmailNotifier()
    
    async def notify_deployment(
        self,
        environment: str,
        status: str,
        version: str,
        recipients: Optional[list] = None,
        details: Optional[str] = None,
        deployment_time: Optional[float] = None
    ):
        """Send deployment notifications to all configured channels."""
        
        # Send Slack notification
        await self.slack.send_deployment_notification(
            environment, status, version, details, deployment_time
        )
        
        # Send email notifications
        if recipients:
            for recipient in recipients:
                await self.email.send_deployment_notification(
                    recipient, environment, status, version, details, deployment_time
                )


# Global notifier instance
deployment_notifier = DeploymentNotifier()
