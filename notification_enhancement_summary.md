<div align="center">

![SCOPE Logo](../static/assets/logo_icon.png)

# 📧 Notification System Enhancement Summary

**Author**: [Sarveshwar Senthil Kumar](https://github.com/SarveshwarSenthilKumar)  
**Repository**: [Engineering Idol - SCOPE System](https://github.com/SarveshwarSenthilKumar/Engineering-Idol)  
**Documentation**: [Live Site](https://sarveshwarsenthilkumar.github.io/SCOPE/)

---

## 📋 TABLE OF CONTENTS

- [📖 Overview](#-overview)
- [🔄 Changes Made](#-changes-made)
- [📁 Enhanced .env File](#-enhanced-env-file)
- [🐍 Updated rasppi.py](#-updated-rasppipy)
- [🔧 Configuration Details](#-configuration-details)
- [🚨 Testing Results](#-testing-results)
- [📈 Future Enhancements](#-future-enhancements)

---

## 📖 Overview

Successfully added comprehensive notification options for fake data mode and organized all environment variables into a .env file.

## 🔄 Changes Made

### 1. Enhanced .env File
**File**: `.env`
- Added all configuration variables from the codebase
- Organized into logical sections:
  - Flask Configuration
  - Alert Thresholds  
  - System Configuration
  - Email Alerts (Gmail SMTP)
  - Gmail Configuration (for rasppi.py)
  - Microsoft Teams Configuration
  - Notification Thresholds
  - **SMS/Text Message Configuration (Twilio)** - NEW
  - Sensor Configuration
  - Radar Configuration
  - Breathing Detection
  - Threat Scoring Configuration
  - Gas Sensor Parameters
  - Audio Configuration

### 2. Updated rasppi.py for Environment Variables
**File**: `rasppi.py`
- Added `import os` and `from dotenv import load_dotenv`
- Updated all hardcoded configuration values to use `os.getenv()`
- Added default values for all environment variables
- Updated ThreatConfig class to use environment variables

### 3. Enhanced NotificationManager with SMS Support
**File**: `rasppi.py`
- Added SMS/Twilio support to NotificationManager class
- Added `send_sms_notification()` method
- Updated alarm and misbehavior notifications to include SMS
- Added Twilio client initialization with error handling
- Added configuration checking for all notification channels

### 4. Enhanced FakeDataGenerator with Notification Testing
**File**: `fake_data_generator.py`
- Added notification testing methods:
  - `send_test_email()`
  - `send_test_teams()`
  - `send_test_sms()`
  - `send_test_notifications()` - tests all channels
- Added proper imports for email, Teams, and SMS functionality
- Added environment variable loading

### 5. Added Web Interface for Notification Testing
**File**: `templates/settings.html`
- Added "Notification Testing (Fake Data Mode)" section
- Added test message textarea
- Added buttons for testing individual channels and all channels
- Added results display area with success/failure indicators
- Added JavaScript function `sendTestNotification()` for API calls

### 6. Added API Endpoint for Notification Testing
**File**: `app.py`
- Added `/api/test-notification` endpoint (POST only)
- Only works in fake data mode (security measure)
- Supports testing individual channels or all channels
- Returns detailed results for each channel
- Proper error handling and logging

## Notification Channels Supported

### Email (Gmail SMTP)
- Uses Gmail SMTP server
- Configurable via environment variables
- Supports both urgent and normal notifications

### Microsoft Teams
- Uses Teams webhook URL
- Configurable via environment variables
- Sends formatted MessageCard notifications

### SMS (Twilio) - NEW
- Uses Twilio SMS service
- Configurable via environment variables
- Message truncation for 160-character limit
- Urgency prefix for critical notifications

## Environment Variables Added

### Twilio SMS Configuration
```bash
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
RECIPIENT_PHONE_NUMBER=+1234567890
```

### Complete Sensor Configuration
```bash
# Sensor thresholds
SPIKE_THRESHOLD_DB=15
LOUD_THRESHOLD_DB=65
VOC_CLEAN_THRESHOLD=50
VOC_ACTIVITY_THRESHOLD=80
VOC_CHEMICAL_THRESHOLD=120
VOC_SMOKING_THRESHOLD=150
VOC_VAPING_THRESHOLD=180
PM_CLEAN_THRESHOLD=10
PM_SMOKE_THRESHOLD=40
PM_VAPING_THRESHOLD=60

# Radar configuration
RADAR_TYPE=auto
RADAR_PORT=/dev/ttyUSB0

# Audio configuration
SAMPLE_RATE=44100
WINDOW_TIME=1
REFERENCE_VOLTAGE=0.05
```

## Usage Instructions

### 1. Configure Environment Variables
Update `.env` file with your actual credentials:
- Gmail SMTP settings for email notifications
- Teams webhook URL for Teams notifications
- Twilio credentials for SMS notifications

### 2. Install Optional Dependencies
For SMS notifications:
```bash
pip install twilio
```

### 3. Test Notifications
1. Visit the Settings page in the web interface
2. Go to the "Notification Testing (Fake Data Mode)" section
3. Enter a custom test message or use the default
4. Click buttons to test individual channels or all channels
5. View results in the display area

### 4. Real Notifications
When threat levels exceed thresholds in production:
- **Critical threats** (≥80): Sends to all configured channels
- **High threats** (≥60): Tracks for misbehavior detection
- **Resolution**: Sends when threats return to normal levels

## Security Features
- Test notifications only work in fake data mode
- Environment variables keep credentials out of code
- Proper error handling prevents system crashes
- Graceful fallback when channels are not configured

## Testing
All notification channels can be tested independently:
- Email: Tests Gmail SMTP connectivity
- Teams: Tests webhook URL and format
- SMS: Tests Twilio credentials and message delivery
- All: Tests all channels simultaneously with detailed results

## Benefits
1. **Complete Configuration Management**: All settings in one .env file
2. **Multi-Channel Support**: Email, Teams, and SMS notifications
3. **Easy Testing**: Web interface for testing all channels
4. **Production Ready**: Proper error handling and security
5. **Flexible**: Each channel can be enabled/disabled independently
