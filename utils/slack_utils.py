import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
import json

class SlackNotifier:
    def __init__(self):
        self.client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
        self.default_channel = os.environ.get("DEFAULT_CHANNEL", "#qa-general")
    
    def send_message(self, channel, message, blocks=None, attachments=None):
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=message,
                blocks=blocks,
                attachments=attachments
            )
            return response
        except SlackApiError as e:
            print(f"Error sending message: {e}")
            return None
    
    def send_test_results(self, channel, test_type, results):
        status_emoji = "✅" if results["failed"] == 0 else "❌"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} {test_type.upper()} Test Results"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total:* {results['total']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Passed:* {results['passed']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Failed:* {results['failed']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration:* {results['duration']:.2f}s"
                    }
                ]
            }
        ]
        
        if results.get("report_url"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{results['report_url']}|View Detailed Report>"
                }
            })
        
        return self.send_message(channel, f"{test_type.upper()} test results", blocks=blocks)
    
    def send_health_alert(self, channel, endpoint_name, url, error):
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ API Health Alert"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Endpoint:* {endpoint_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*URL:* {url}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue:* {error}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]
        
        return self.send_message(channel, "API Health Alert", blocks=blocks)
    
    def send_daily_summary(self, channel, api_results, ui_results):
        total_passed = api_results["passed"] + ui_results["passed"]
        total_tests = api_results["total"] + ui_results["total"]
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        status_emoji = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Daily Test Summary - {datetime.now().strftime('%Y-%m-%d')}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*API Tests:* {api_results['passed']}/{api_results['total']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*UI Tests:* {ui_results['passed']}/{ui_results['total']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Success Rate:* {success_rate:.1f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Duration:* {api_results['duration'] + ui_results['duration']:.1f}s"
                    }
                ]
            }
        ]
        
        return self.send_message(channel, "Daily Test Summary", blocks=blocks)
    
    def send_deployment_notification(self, channel, environment, status, version=None):
        emoji = "🚀" if status == "success" else "❌"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Deployment {status.title()}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Environment:* {environment}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:* {status.title()}"
                    }
                ]
            }
        ]
        
        if version:
            blocks[1]["fields"].append({
                "type": "mrkdwn",
                "text": f"*Version:* {version}"
            })
        
        return self.send_message(channel, f"Deployment {status}", blocks=blocks)
    
    def get_user_info(self, user_id):
        try:
            response = self.client.users_info(user=user_id)
            return response["user"]
        except SlackApiError:
            return None
    
    def get_channel_info(self, channel_id):
        try:
            response = self.client.conversations_info(channel=channel_id)
            return response["channel"]
        except SlackApiError:
            return None

def format_test_summary(results):
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": results.get("total", 0),
        "passed": results.get("passed", 0),
        "failed": results.get("failed", 0),
        "skipped": results.get("skipped", 0),
        "success_rate": (results.get("passed", 0) / results.get("total", 1)) * 100
    }
    return summary

def create_progress_bar(passed, total, width=20):
    if total == 0:
        return "█" * width
    
    progress = int((passed / total) * width)
    bar = "█" * progress + "░" * (width - progress)
    return f"{bar} {passed}/{total}"