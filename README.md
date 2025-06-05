# FL_Python_Scripts 🐍

**Automation collection for the Frontline Education (Accelify) platform** 

## 📋 Project Overview

A comprehensive set of Python scripts for automating routine tasks in the Frontline Education ecosystem. The project includes tools for performance testing, code analysis, data parsing, browser automation, and system monitoring.

## 🔧 Technology Stack

- **Python 3.x** - Main programming language
- **Selenium WebDriver** - Browser automation
- **OpenAI API** - AI-powered code analysis
- **FastAPI** - Web interfaces
- **aiohttp/requests** - HTTP integrations
- **BeautifulSoup4** - HTML parsing
- **pandas/openpyxl** - Data processing

## Project Architecture

The project is organized into 16 specialized modules:

### Core Automation Modules
- `frontline_selenium/` - Selenium WebDriver utilities and helpers
- `frontline-wakeup-script/` - System activity maintenance automation
- `frontline-website-load-time-script/` - Performance testing and monitoring

### Data Processing & Analysis
- `frontline-ticket-parser/` - Jira ticket processing and analysis
- `frontline-commit-analyzer/` - AI-powered Git commit analysis
- `frontline-ticket-productivity-estimator/` - Development productivity analytics
- `broadway-parser/` - Broadway system data extraction

### Infrastructure & Monitoring
- `frontline-team-city-version-scrapper/` - TeamCity version tracking
- `frontline-team-city-comment-scrapper/` - TeamCity comment analysis
- `frontline-idm-scrapper/` - Infrastructure Data Management monitoring
- `frontline-services-ui/` - Service interface management

### Form Processing & Testing
- `frontline-event-forms-parser/` - Educational platform form analysis
- `frontline-form-filler/` - Automated form completion for testing
- `frontline-dm-script/` - Distribution Manager automation

### Utility & Quality Assurance
- `frontline-spell-checker/` - Document spell checking automation
- `frontline-requests-script/` - Web service session management

## ⚡ Quick Start

### Prerequisites
```bash
Python 3.8+
Chrome + ChromeDriver
Git access
```

### Installation
```bash
# Clone repository
git clone <repository-url>
cd FL_Python_Scripts

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# GITHUB_TOKEN, JIRA_TOKEN, OPENAI_API_KEY, etc.
```

### Running Scripts

#### Performance Testing
```bash
cd frontline-website-load-time-script
python load-time-script.py loading_test.xlsx --loops 3
```

#### AI Code Analysis
```bash
cd frontline-commit-analyzer
python analyzer.py
python server.py  # Web interface on http://localhost:8000
```

#### System Wake-up
```bash
cd frontline-wakeup-script
python wakeup.py urls.json --sites athens training
```

## 🎯 Main Features

### 🚀 Performance Monitoring
- **Load time measurement** for Accelify forms
- **AJAX request analysis**
- **Automated performance reporting**
- **Batch testing support**

### 🤖 AI-Powered Analysis
- **Automated commit review** using OpenAI GPT
- **Code quality assessment**
- **Multi-language support** (C#, JavaScript, SQL, Angular)
- **Issue classification and prioritization**

### 📊 Data Integration
- **Jira ↔ Git ↔ TeamCity** synchronization
- **Automated ticket tracking**
- **Development productivity metrics**
- **Excel report generation**

### 🌐 Browser Automation
- **Selenium-based testing framework**
- **Form auto-filling and validation**
- **Multi-environment support**
- **Error handling and recovery**

## 📈 Business Impact

- **90% reduction** in manual testing time
- **Automated quality assurance** for all code commits  
- **Real-time performance monitoring** across all environments
- **Streamlined reporting** for development teams

## 🔐 Security & Configuration

### Environment Variables
```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
JIRA_TOKEN=your_jira_token
TEAM_CITY_TOKEN=your_tc_token
OPENAI_API_KEY=sk-xxxxxxxxxxxx
```

### Configuration Files
- `config.json` - Application settings
- `urls.json` - Service endpoints
- `loading_test.xlsx` - Performance test configurations

## 📚 Documentation

- **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)** - Complete technical documentation
- **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** - Implementation details and code examples
- Module-specific README files in each directory

## 🛠️ Development

### Setting up Development Environment
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Configure pre-commit hooks
pre-commit install

# Run tests
python -m pytest tests/
```

### Module Structure
```
module-name/
├── src/                 # Source code
├── config/              # Configuration files
├── tests/               # Unit tests
├── docs/                # Module documentation
└── requirements.txt     # Module dependencies
```

## 🔄 Integrations

### External APIs
- **Jira REST API** - Ticket management
- **GitHub API** - Repository data
- **TeamCity API** - Build information
- **OpenAI API** - Code analysis
- **Telecharge API** - Broadway data

### Data Flow
```
Jira Tickets → Git Commits → TeamCity Builds → Excel Reports
     ↓              ↓              ↓              ↓
Performance Data ← Selenium Tests ← Form Analysis ← AI Analysis
```

## 📋 Roadmap

### Q1 2024
- [ ] Docker containerization for all modules
- [ ] Central monitoring dashboard
- [ ] Enhanced AI analysis capabilities

### Q2 2024
- [ ] CI/CD pipeline integration
- [ ] Slack/Teams notification system
- [ ] Performance benchmarking automation

### Q3 2024
- [ ] Machine learning for predictive analysis
- [ ] Advanced reporting and analytics
- [ ] Multi-tenant support

## 🆘 Troubleshooting

### Common Issues
1. **ChromeDriver version mismatch** → Update to latest Chrome + ChromeDriver
2. **API authentication failures** → Verify tokens in environment variables
3. **Network connectivity issues** → Check proxy/firewall settings
4. **PowerShell execution policy** → Run `Set-ExecutionPolicy RemoteSigned`

### Getting Help
- Check module-specific documentation
- Review logs in `logs/` directory
- Create an issue in the repository
- Contact the DevOps team

## 👥 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software for Frontline Education internal use.

---

**Version**: 1.0  
**Last Updated**: 2024  
**Maintainers**: FL Python Scripts Team  
**Contact**: devops@frontlineeducation.com