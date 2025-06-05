# FL_Python_Scripts - Technical Guide

## Overview

This guide covers technical implementation details for the FL_Python_Scripts automation suite, focusing on real components and patterns used across the project.

## Core Components

### SeleniumHelper Class

The main automation framework located in `frontline_selenium/selenium_helper.py`:

```python
from frontline_selenium.selenium_helper import SeleniumHelper

# Configure logger and options
SeleniumHelper.setup_logger(logger)
SeleniumHelper.set_options({"disable_filler": False})

# Core functionality
driver = webdriver.Chrome()
SeleniumHelper.login_user(url, driver, username, password)
SeleniumHelper.wait_for_form_page_load(driver)

# Performance measurement
load_time = SeleniumHelper.measure_form_page_load_time(driver)
save_time = SeleniumHelper.measure_form_save_time(driver)
```

**Key Methods:**
- `wait_for_form_page_load()` - Waits for Accelify forms to load
- `measure_form_save_time()` - Times form save operations with auto-filling
- `get_ajax_requests()` - Captures AJAX requests for analysis
- `wait_for_form_save_popup()` - Waits for save confirmation

### Configuration Pattern

Most modules use JSON configuration files:

```python
# Standard configuration loading
import json

def load_config():
    with open("configuration.json", "r") as config_file:
        return json.load(config_file)

# Example configuration.json
{
  "jira_host": "frontlineeducation.atlassian.net",
  "teamcity_host": "teamcity.domain.com",
  "repository_path": "C:\\repos\\project",
  "ssh_key_path": "C:\\keys\\id_rsa"
}
```

### Environment Variables

Required tokens for API access:

```bash
set GITHUB_TOKEN=ghp_xxxxxxxxxxxx
set JIRA_TOKEN=your_jira_token
set TEAM_CITY_TOKEN=your_tc_token
set OPENAI_API_KEY=sk-xxxxxxxxxxxx
```

## Module-Specific Implementation

### Commit Analyzer (`frontline-commit-analyzer/`)

**Main Class**: `Analyzer` in `analyzer.py`

```python
from codeReview import CodeReviewProvider

class Analyzer:
    def __init__(self):
        self.codereview_provider = CodeReviewProvider(chat_completion=True)
        self.github_url = f"https://api.github.com/repos/{owner}/{repo}"
        
    async def analyze_commits(self, hours=12):
        start = self.utc_now - timedelta(hours=hours)
        await self.process_commits(start)
        
    async def review_file(self, file):
        review = await loop.run_in_executor(
            None, 
            self.codereview_provider.get_code_review, 
            file.get('patch'), 
            file.get('filename')
        )
```

**Usage:**
```bash
cd frontline-commit-analyzer
python analyzer.py
python server.py  # FastAPI web interface
```

### Website Load Time Script (`frontline-website-load-time-script/`)

Performance testing with Excel configuration:

```python
# Load test configuration from Excel
import openpyxl

wb = openpyxl.load_workbook("loading_test.xlsx")
sheet = wb.active

# Execute performance tests
for row in sheet.iter_rows(min_row=2):
    url = row[0].value
    username = row[1].value
    # Measure load time using SeleniumHelper
```

### Ticket Parser (`frontline-ticket-parser/`)

Integrates Jira, Git, and TeamCity:

```python
# Async API calls to Jira
async def get_issues_from_jira(session, jira_url, login, token):
    auth = aiohttp.BasicAuth(login=login, password=token)
    jql = 'labels=jira_escalated and project="CW-0575"'
    url = f'{jira_url}?jql={jql}&startAt=0&maxResults=50'
    
    async with session.get(url, headers=headers, auth=auth) as response:
        data = await response.json()
        return data.get('issues', [])

# PowerShell integration for Git operations
async def find_in_git(ticket, script_path, repository_path):
    process = await asyncio.create_subprocess_exec(
        'powershell', '-File', script_path,
        '-Repository_path', repository_path,
        '-Ticket_number', ticket['key'],
        stdout=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return json.loads(stdout.decode('utf-8'))
```

### Page Form Filler (`frontline_selenium/page_filler.py`)

Automated form filling functionality:

```python
from frontline_selenium.page_filler import PageFormFiller

# Used by SeleniumHelper.measure_form_save_time()
PageFormFiller.fill_form(driver)

# Fills various form elements:
# - Text inputs and textareas
# - Dropdowns and select elements  
# - Checkboxes and radio buttons
# - Rich text editors (Kendo)
```

## Common Patterns

### Async HTTP Client

Standard pattern for API integrations:

```python
import aiohttp
from aiohttp import TCPConnector

async with aiohttp.ClientSession(
    connector=TCPConnector(verify_ssl=False)
) as session:
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(url, headers=headers) as response:
        return await response.json()
```

### Error Handling

Retry logic with timeout:

```python
attempt = 0
while attempt < 3:
    try:
        attempt += 1
        async with session.get(url, headers=headers) as resp:
            return await resp.json()
    except aiohttp.ClientOSError as e:
        print(f'Error: {e}')
        await asyncio.sleep(1)
```

### Logging Setup

Standard logging configuration:

```python
import logging
from datetime import datetime

def configure_logger(file_name: str) -> logging.Logger:
    logger = logging.getLogger("main")
    formatter = logging.Formatter("%(asctime)s - %(message)s")
    timestamp = datetime.now().strftime("%m-%d-%y_%H-%M")
    fh = logging.FileHandler(f"{file_name}_{timestamp}.log")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger
```

### Excel Integration

Working with Excel files:

```python
import openpyxl

# Read configuration
wb = openpyxl.load_workbook("config.xlsx")
sheet = wb.active

# Write results
for row_idx, result in enumerate(results, start=2):
    sheet.cell(row=row_idx, column=1, value=result['name'])
    sheet.cell(row=row_idx, column=2, value=result['time'])

wb.save("results.xlsx")
```

## JavaScript Integration

### AJAX Monitoring

`frontline_selenium/util_scripts/get_requests.js` - Captures network requests:

```javascript
// Used by SeleniumHelper.get_ajax_requests()
// Returns array of {url, status, method} objects
```

### Form Auto-filling

JavaScript execution for complex form interactions:

```python
# Execute JavaScript in browser context
driver.execute_script("""
    $('.form input[type="text"]').val('test data');
    $('.form select').each(function() {
        $(this).val($(this).find('option:nth-child(2)').val());
    });
""")
```

## API Integrations

### GitHub API
```python
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {github_token}"
}
url = f"https://api.github.com/repos/{owner}/{repo}/commits"
```

### Jira API
```python
auth = aiohttp.BasicAuth(login=jira_login, password=jira_token)
url = f"https://{jira_host}/rest/api/2/search"
```

### TeamCity API
```python
headers = {
    "Authorization": f"Bearer {teamcity_token}",
    "Accept": "application/json"
}
url = f"https://{teamcity_host}/app/rest/projects"
```

## Testing and Deployment

### Running Tests
```bash
# Performance testing
cd frontline-website-load-time-script
python load-time-script.py loading_test.xlsx --loops 3

# AI analysis
cd frontline-commit-analyzer  
python analyzer.py

# Ticket parsing
cd frontline-ticket-parser
python ticket_parser.py
```

### Common Issues

1. **ChromeDriver version mismatch**
   - Update Chrome and ChromeDriver to matching versions
   - Ensure ChromeDriver is in PATH

2. **API authentication failures**
   - Verify environment variables are set correctly
   - Check token permissions and expiration

3. **PowerShell execution policy**
   ```powershell
   Set-ExecutionPolicy RemoteSigned
   ```

4. **SSL certificate issues**
   - Use `TCPConnector(verify_ssl=False)` for internal services

---

This guide covers the actual implementation patterns used in FL_Python_Scripts. Refer to module-specific README files for detailed usage instructions.