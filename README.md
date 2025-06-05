# FL_Python_Scripts 🐍

**Automation collection for the Frontline Education (Accelify) platform**

## 📋 What is this?

FL_Python_Scripts is a comprehensive suite of Python automation tools designed to streamline operations within the Frontline Education ecosystem. The project includes 16 specialized modules for performance testing, AI-powered code analysis, data processing, and browser automation.

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** - Main runtime
- **Node.js 16+** - Required for Angular web interface  
- **Chrome + ChromeDriver** - Browser automation
- **Angular CLI** - For web interface management
- **Git access** to repositories

### Installation
```bash
# 1. Clone repository
git clone https://github.com/leoshum/FL_Python_Scripts.git
cd FL_Python_Scripts

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Angular CLI globally (for web interface)
npm install -g @angular/cli

# 4. Install Angular dependencies for web interface
cd frontline-services-ui/services
npm install
cd ../..
```

### Web Interface Setup (frontline-services-ui)
The project includes a modern Angular + Python web interface for managing all automation scripts:

```bash
# Start the web interface (both Angular frontend + Python backend)
cd frontline-services-ui
powershell -ExecutionPolicy Bypass -File start.ps1

# Or manually:
# Terminal 1 - Angular frontend (port 4200)
cd frontline-services-ui/services
ng serve

# Terminal 2 - Python backend (port 34443)  
cd frontline-services-ui
python server.py
```

**Access**: http://localhost:4200 (requires both servers running)

### Environment Setup
```bash
# Required API tokens
set GITHUB_TOKEN=your_github_token
set JIRA_TOKEN=your_jira_token  
set OPENAI_API_KEY=your_openai_key
set TEAM_CITY_TOKEN=your_teamcity_token
```

## ⚡ Main Use Cases

### Performance Testing
```bash
cd frontline-website-load-time-script
python load-time-script.py loading_test.xlsx --loops 3
```

### AI Code Analysis
```bash
cd frontline-commit-analyzer
python analyzer.py
python server.py  # Web interface at http://localhost:8000
```

### System Wake-up
```bash
cd frontline-wakeup-script
python wakeup.py urls.json --sites athens training
```

### Ticket Processing
```bash
cd frontline-ticket-parser
python ticket_parser.py
```

## 🛠️ Technology Stack

- **Python 3.x** - Main language
- **Angular 15** - Web frontend interface
- **Node.js** - Angular build system  
- **TypeScript** - Frontend development
- **Selenium WebDriver** - Browser automation
- **OpenAI API** - AI code analysis
- **FastAPI** - Web interfaces
- **aiohttp/requests** - HTTP integrations
- **pandas/openpyxl** - Data processing

## 📊 Key Features

- ⚡ **Performance monitoring** for Accelify forms
- 🤖 **AI-powered commit analysis** with OpenAI
- 🔄 **Automated ticket tracking** (Jira ↔ Git ↔ TeamCity)
- 🌐 **Browser automation** for testing and validation
- 📈 **Real-time reporting** and analytics

## 📚 Documentation

- **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)** - Complete project overview, business context, and module descriptions
- **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** - Implementation details, code examples, and best practices

---

> 💡 **New to the project?** Start with [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for business context and architecture overview, then refer to [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) for implementation details.