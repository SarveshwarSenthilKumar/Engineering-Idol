<div align="center">

![SCOPE Logo](../../static/assets/logo_icon.png)

# 📚 SCOPE System Documentation

**Author**: [Sarveshwar Senthil Kumar](https://github.com/SarveshwarSenthilKumar)  
**Repository**: [Engineering Idol - SCOPE System](https://github.com/SarveshwarSenthilKumar/Engineering-Idol)  
**Documentation**: [Live Site](https://sarveshwarsenthilkumar.github.io/SCOPE/)

---

System for Comprehensive Observation and Protection of Environments - Advanced environmental monitoring and threat detection system.

## 🚀 Quick Start

### 📖 Viewing Documentation

**🌐 Live Documentation**: [https://sarveshwarsenthilkumar.github.io/SCOPE/](https://sarveshwarsenthilkumar.github.io/SCOPE/)

Open the documentation directly in your browser:

```bash
# Simply open the HTML file in your browser
open scope-docs.html
# or double-click the file in your file explorer
```

### 🐍 Running the Documentation Server

```bash
python app.py
```

The documentation will be available at: `http://localhost:5001`

## 📖 Documentation Overview

This comprehensive documentation covers the complete SCOPE system including:

- **🏠 System Overview**: Architecture and components
- **🏢 Real-World Applications**: Educational, corporate, healthcare, retail
- **🔧 Hardware Components**: mmWave radar, sensors, IoT integration
- **💻 Software Components**: Flask app, AI engine, database
- **🌐 Web Application**: Dashboard and monitoring interface
- **🗄️ Database Schema**: SQLite structure and relationships
- **🔌 API Endpoints**: REST/SSE/JSON interfaces
- **🔒 Security and Authentication**: User management and access control
- **📡 Real-time Monitoring**: Live data streaming and alerts
- **📊 Analytics and Reporting**: AI-powered analysis
- **📧 Notifications**: Email, Teams, alert systems
- **🏢 Multi-Environment**: Multiple zone monitoring
- **🎮 Scenario Simulation**: Training and testing
- **👥 User Management**: Role-based access
- **💾 Data Management**: Storage and retrieval
- **⚙️ Configuration**: System settings
- **🚀 Deployment**: Installation guides
- **🔗 Integration**: Third-party systems
- **⚡ Performance**: Optimization
- **🧠 Advanced Features**: AI capabilities
- **🧪 Testing**: Quality assurance
- **🎯 Scoring Playground**: Interactive threat scoring
- **🐙 GitHub**: Repository and source code

## 🎨 Features

### Enhanced Search System
- **'S' Key Shortcut**: Press 's' anywhere to activate search
- **Popup Interface**: Modal-style search results
- **Keyboard Navigation**: Arrow keys for result navigation
- **Dark Mode Compatible**: Full theme support

### Interactive Scoring Playground
- **Real-time Calculations**: Live threat scoring updates
- **Component Breakdown**: Individual score contributions
- **Educational**: Learn how SCOPE calculates threats
- **Range Validation**: Proper 0-100 scoring range

### Quick Guide System
- **Comprehensive Help**: Built-in user guide
- **Keyboard Shortcuts**: All navigation shortcuts
- **Mobile Support**: Touch-friendly interface
- **Dark Mode**: Consistent theming

### Recent Updates
- **✅ Event History & Analytics Fixed**: Backend routes and frontend templates now working properly
- **🌬️ Air Quality Monitoring**: MQ135 VOC and PMS5003 particle sensor integration
- **📊 Enhanced Data Generation**: Current time-based fake data with realistic distribution

## � Mobile Compatibility

- Touch-friendly buttons and controls
- Responsive layout for all screen sizes
- Swipe gestures for navigation
- Optimized performance for mobile devices

## 🌙 Dark Mode

Complete dark mode support with:
- High contrast color schemes
- Persistent theme selection
- Smooth transitions between themes
- Accessibility-compliant color ratios

## �🔧 Technical Details

- **Framework**: Flask 5.3.0
- **Styling**: Bootstrap 5 + Custom CSS
- **JavaScript**: Vanilla JS with modern features
- **Responsive**: Mobile-first design approach
- **Performance**: Optimized loading and interactions

## � Documentation Structure

```
documentation/
├── README.md           # This file
├── app.py              # Flask server for documentation
├── scope-docs.html     # Main documentation page (standalone)
└── static/
    ├── js/
    │   └── scope-docs.js  # Documentation JavaScript (44KB)
    └── css/
        └── scope-docs.css # Documentation styles (43KB)
```

## 🌐 Access Points

### Documentation
- **🌐 Live Site**: [https://sarveshwarsenthilkumar.github.io/SCOPE/](https://sarveshwarsenthilkumar.github.io/SCOPE/)
- **📄 Direct Access**: Open `scope-docs.html` in any browser
- **🔧 Documentation Server**: Run `python app.py` for `http://localhost:5001`
- **✨ Full Features**: Complete documentation with all interactive elements

### Main SCOPE Application
- **🌐 Web Interface**: `http://localhost:5000` (when main app.py is running)
- **📡 Real-time Data**: Live sensor monitoring and threat detection
- **🎛️ Interactive Dashboard**: Full system control and monitoring

## � Key Features

### Core Capabilities
- **🔍 Real-time Monitoring**: Continuous surveillance using multiple sensor types
- **🧠 AI-Powered Analysis**: Machine learning algorithms for threat detection
- **🏢 Multi-Environment Support**: Simultaneous monitoring of multiple areas/zones
- **🌐 Web-Based Interface**: Modern responsive dashboard accessible from any device
- **📈 Automated Reporting**: AI-generated comprehensive reports with recommendations
- **🚨 Alert System**: Multi-channel notifications for critical events

### Air Quality Monitoring
- **🌬️ VOC Detection**: MQ135 sensor for volatile organic compounds
- **🫠 Particle Sensing**: PMS5003 for PM1.0, PM2.5, PM10 measurements
- **🚭 Smoking/Vaping Detection**: Advanced pattern recognition
- **📊 Air Quality Index**: Real-time AQI calculation
- **⚠️ Auto-Alarms**: Automatic threat escalation for extreme values

## 📊 System Statistics

- **3,699+** Lines of production code
- **70+** Database fields
- **4** Environment support zones
- **🔴 Real-time Monitoring** and alerts
- **🧠 AI-powered Threat detection**
- **🔌 Multi-sensor Integration**
- **🌬️ Advanced Air Quality monitoring**

## 🔗 Integration

This documentation server is completely separate from the main SCOPE application:
- **No routing conflicts** with the main app
- **Independent deployment** - can be hosted separately
- **Focused purpose** - documentation only, no sensor data

---

**📚 Live Documentation**: [https://sarveshwarsenthilkumar.github.io/SCOPE/](https://sarveshwarsenthilkumar.github.io/SCOPE/)

**Note**: This documentation (`scope-docs.html`) is completely standalone and can be viewed without running the Flask server. For a server-based experience, run `python app.py` to access the documentation at `http://localhost:5001`. The main SCOPE application provides the live monitoring and threat detection capabilities.
