<div align="center">

![SCOPE Logo](../static/assets/logo_icon.png)

# 📧 Notification Setup Guide

**Author**: [Sarveshwar Senthil Kumar](https://github.com/SarveshwarSenthilKumar)  
**Repository**: [Engineering Idol - SCOPE System](https://github.com/SarveshwarSenthilKumar/Engineering-Idol)  
**Documentation**: [Live Site](https://sarveshwarsenthilkumar.github.io/SCOPE/)

---

## 📋 TABLE OF CONTENTS

- [📧 Gmail Configuration](#-gmail-configuration)
- [📱 Microsoft Teams Configuration](#-microsoft-teams-configuration)
- [📞 Twilio SMS Configuration](#-twilio-sms-configuration)
- [🔧 Advanced Settings](#-advanced-settings)
- [🚨 Testing Notifications](#-testing-notifications)
- [🛠️ Troubleshooting](#️-troubleshooting)

---

## 📧 Gmail Configuration

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings → Security → 2-Step Verification → App passwords
   - Generate a new app password for "SCOPE Monitor"
   - Use this password in the configuration (NOT your regular password)

3. **Update Configuration** in `rasppi.py`:
   ```python
   GMAIL_SENDER_EMAIL = "your-email@gmail.com"
   GMAIL_SENDER_PASSWORD = "your-generated-app-password"
   GMAIL_RECIPIENT_EMAIL = "front-office@school.edu"
   ```

## Microsoft Teams Configuration

1. **Create a Teams Webhook**:
   - Go to Microsoft Teams → Channel → Connectors → Incoming Webhook
   - Add "Incoming Webhook" connector
   - Configure name and optionally upload an image
   - Copy the webhook URL

2. **Update Configuration** in `rasppi.py`:
   ```python
   TEAMS_WEBHOOK_URL = "https://your-tenant.webhook.office.com/webhookb3/..."
   ```

## Notification Thresholds

The system uses these thresholds:

- **Alarm Notification**: Threat ≥ 80 (Critical/High threat levels)
- **Misbehavior Tracking**: Threat ≥ 60 (Starts tracking misbehavior)
- **Misbehavior Resolution**: Threat ≤ 40 (Sends "all clear" notification)

## Notification Types

### 🚨 Alarm Notifications (Urgent)
- Triggered when threat level reaches critical (≥80)
- Sent via BOTH Gmail and Teams
- Includes detailed threat breakdown and detected issues
- 5-minute cooldown between same notification type

### ✅ Misbehavior Resolution Notifications (Info)
- Triggered when threat drops to safe levels (≤40) after misbehavior was detected
- Sent via BOTH Gmail and Teams
- Includes event duration and resolution details
- 5-minute cooldown between same notification type

## Features

- **Dual Notification**: Both Gmail and Teams for redundancy
- **Smart Cooldown**: Prevents notification spam
- **Detailed Context**: Includes threat components, trends, and sensor data
- **Professional Formatting**: Rich formatting for both email and Teams
- **Error Handling**: Graceful fallback if one service fails
- **Graceful Degradation**: System works without credentials - notifications are simply disabled
- **Configuration Validation**: Checks credentials on startup and provides clear warnings

## Testing

Test the notification system by:
1. Temporarily lowering `ALARM_NOTIFICATION_THRESHOLD` to 30
2. Running the system and verifying notifications arrive
3. Restoring the original threshold
4. Checking system logs for notification status

## Security Notes

- Store credentials securely (consider environment variables)
- Use app-specific passwords, not main account passwords
- Limit webhook permissions to minimum required
- Regularly rotate passwords and webhooks
- Monitor notification logs for unauthorized access
