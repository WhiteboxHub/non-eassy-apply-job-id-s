import os
import smtplib
import json
from email.message import EmailMessage
from datetime import datetime
from bot.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

APPLICATION_NAME = "LinkedIn Non-Easy Apply Job Extractor"

class EmailReporter:
    @staticmethod
    def send_report(results: dict, run_name: str = None):
        """
        Sends an HTML summary report via SMTP based on extraction results.
        """
        # Validate SMTP configuration
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_user = os.getenv("SMTP_USERNAME")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        receiver = os.getenv("REPORT_RECEIVER_EMAIL")
        sender = os.getenv("SENDER_EMAIL") or smtp_user

        if not all([smtp_server, smtp_port, smtp_user, smtp_pass, receiver]):
            logger.warning("[EMAIL] SMTP configurations are not fully set up. Skipping email report.")
            return

        try:
            smtp_port = int(smtp_port)
        except ValueError:
            logger.error(f"[EMAIL] Invalid SMTP_PORT: {smtp_port}")
            return

        # Extract data for the report
        jobs_saved = results.get("jobs_saved", 0)
        jobs_sample = results.get("jobs_sample", [])
        status = results.get("status", "unknown")
        timestamp = results.get("timestamp", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Breakdown by Easy Apply vs Standard
        easy_count = sum(1 for j in jobs_sample if j.get('is_easy_apply'))
        standard_count = len(jobs_sample) - easy_count

        # Build HTML for Sample Job Links (Max 25 total)
        MAX_LINKS = 25
        links_section = ""
        
        if jobs_sample:
            links_list = ""
            for i, job in enumerate(jobs_sample[:MAX_LINKS]):
                title = job.get("title") or "Unknown Title"
                url = job.get("apply_url") or job.get("url")
                type_label = "⚡ Easy Apply" if job.get('is_easy_apply') else "🔗 Standard"
                
                links_list += f"""
                <li style="margin-bottom: 8px;">
                    <a href="{url}" style="color: #3498db; text-decoration: none; font-size: 14px; font-weight: 500;">{title}</a>
                    <br><span style="color: #95a5a6; font-size: 11px;">{type_label}</span>
                </li>
                """
            
            remaining = jobs_saved - len(jobs_sample[:MAX_LINKS])
            more_footer = f'<li style="list-style: none; color: #95a5a6; font-size: 12px; margin-top: 4px;">... and {remaining} more jobs</li>' if remaining > 0 else ""
            
            links_section = f"""
            <div style="margin-top: 20px;">
                <h4 style="color: #34495e; margin-bottom: 10px; border-left: 3px solid #3498db; padding-left: 10px; font-size: 15px;">Sample Listings</h4>
                <ul style="padding-left: 20px; margin: 0; color: #7f8c8d;">
                    {links_list}
                    {more_footer}
                </ul>
            </div>
            """
        else:
            links_section = "<p style='color: #95a5a6; font-style: italic;'>No new jobs found in this run.</p>"

        # Run Name Badge
        run_badge = ""
        if run_name:
            run_badge = f"""
            <div style="display: inline-block; background-color: #3498db; color: white; padding: 4px 12px; border-radius: 50px; font-size: 12px; font-weight: bold; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px;">
                {run_name}
            </div>
            """

        html_content = f"""
        <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f9f9f9; color: #333; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    {run_badge}
                    <h2 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 15px; margin-top: 0;">{APPLICATION_NAME}</h2>
                    
                    <p style="font-size: 16px; color: #555;">The automated LinkedIn extraction has completed.</p>

                    <div style="background: #ebf5fb; border-radius: 8px; padding: 20px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="display: block; font-size: 14px; color: #5dade2; text-transform: uppercase; font-weight: bold; margin-bottom: 5px;">Total Jobs Extracted</span>
                            <span style="font-size: 32px; font-weight: bold; color: #2e86c1;">{jobs_saved}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="display: block; font-size: 12px; color: #7f8c8d;">Status: <strong style="color: {'#27ae60' if status == 'success' else '#e74c3c'}">{status.upper()}</strong></span>
                            <span style="display: block; font-size: 12px; color: #7f8c8d;">Time: {timestamp}</span>
                        </div>
                    </div>

                    <div style="margin-bottom: 25px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 10px; background: #f8f9fa; border-radius: 6px 0 0 6px; border-right: 2px solid #fff;">
                                    <span style="display: block; font-size: 11px; color: #95a5a6; text-transform: uppercase;">Standard Jobs</span>
                                    <span style="font-size: 18px; font-weight: bold; color: #34495e;">{standard_count}</span>
                                </td>
                                <td style="padding: 10px; background: #f8f9fa; border-radius: 0 6px 6px 0;">
                                    <span style="display: block; font-size: 11px; color: #95a5a6; text-transform: uppercase;">Easy Apply</span>
                                    <span style="font-size: 18px; font-weight: bold; color: #34495e;">{easy_count}</span>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <div style="margin-top: 30px; border-top: 2px solid #f1f1f1; padding-top: 20px;">
                        {links_section}
                    </div>

                    <p style="font-size: 13px; color: #95a5a6; margin-top: 35px; border-top: 1px solid #eee; padding-top: 20px; text-align: center;">
                        This is an automated report from {APPLICATION_NAME}.<br>
                        Logs are available in the project directory.
                    </p>
                </div>
            </body>
        </html>
        """

        msg = EmailMessage()
        subject_prefix = f"[{run_name}] " if run_name else ""
        msg["Subject"] = f"{subject_prefix}[{APPLICATION_NAME}] {jobs_saved} jobs extracted"
        msg['From'] = sender
        msg['To'] = receiver
        
        msg.set_content(
            f"{APPLICATION_NAME}: Please enable HTML to view this report summary.\n"
            f"Total Jobs Extracted: {jobs_saved}\n"
            f"Status: {status}\n"
            f"Time: {timestamp}"
        )
        msg.add_alternative(html_content, subtype='html')

        # Send the email
        try:
            logger.info(f"[EMAIL] Connecting to {smtp_server}:{smtp_port} to send report...")
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            logger.info(f"[EMAIL] Successfully sent report to {receiver}")
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send email: {e}")

email_reporter = EmailReporter()
