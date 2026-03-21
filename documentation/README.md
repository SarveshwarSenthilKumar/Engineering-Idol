# SCOPE System Documentation

Standalone documentation server for the SCOPE System.

## 🚀 Quick Start

### Running the Documentation Server

```bash
cd documentation
python app.py
```

The documentation will be available at: `http://localhost:5001`

### Features

- 📚 **Complete Documentation**: Full SCOPE system documentation
- 🔍 **Enhanced Search**: Popup search with keyboard shortcuts ('s' key)
- 🎨 **Dark Mode Support**: Full theme compatibility
- 📱 **Responsive Design**: Mobile-friendly interface
- ⌨️ **Keyboard Navigation**: Arrow keys and shortcuts
- 🎯 **Interactive Elements**: Scoring playground, quick guide

### Documentation Structure

```
documentation/
├── app.py              # Flask server for documentation
├── scope-docs.html    # Main documentation page
├── static/
│   ├── js/
│   │   └── scope-docs.js  # Documentation JavaScript
│   └── css/
│       └── scope-docs.css # Documentation styles
└── README.md           # This file
```

### Port Configuration

The documentation server runs on port **5001** to avoid conflicts with the main SCOPE app (port 5000).

### Integration

This documentation server is completely separate from the main SCOPE application:
- **No routing conflicts** with the main app
- **Independent deployment** - can be hosted separately
- **Focused purpose** - documentation only, no sensor data

## 📚 Documentation Sections

The documentation includes comprehensive sections covering:

- 🏠 **System Overview**: Architecture and components
- 🔧 **Installation & Setup**: Deployment guides
- 📊 **Hardware Integration**: Sensor configurations  
- 🎯 **Threat Scoring**: Interactive scoring playground
- 🌐 **Web Interface**: Dashboard and monitoring
- 📈 **Analytics & Reporting**: Data analysis features
- 🔒 **Security**: Authentication and access control
- 🚀 **Performance**: Optimization and monitoring

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

## 🔧 Technical Details

- **Framework**: Flask 5.3.0
- **Styling**: Bootstrap 5 + Custom CSS
- **JavaScript**: Vanilla JS with modern features
- **Responsive**: Mobile-first design approach
- **Performance**: Optimized loading and interactions

## 📱 Mobile Compatibility

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

---

**Note**: This documentation server is separate from the main SCOPE application to avoid routing conflicts and allow independent deployment.
