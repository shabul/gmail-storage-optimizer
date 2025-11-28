# Gmail Storage Optimizer

**Author:** Shabul

## The Problem

Like many Gmail users, I hit the 15GB storage limit on my Google account. The constant notifications to upgrade to Google One were frustrating, especially when most of my storage was consumed by thousands of promotional emails, newsletters, and automated notifications that I never read.

I needed a solution that would:
- Systematically clean up bulk emails from specific senders
- Preserve important personal correspondence
- Handle Gmail's deletion limits gracefully
- Be reusable for ongoing maintenance

This project is the result of that need.

## What This Does

Gmail Storage Optimizer is a Python-based automation suite that helps you reclaim Gmail storage space without paying for Google One. It uses Selenium to automate the process of identifying and deleting bulk emails while implementing multiple safety mechanisms to protect important messages.

### Key Features

**Intelligent Email Cleaning**
- Processes multiple email addresses in parallel batches
- Handles Gmail's 100-email deletion limit automatically
- Implements random delays to avoid rate limiting
- Maintains persistent login sessions via Chrome profiles

**Safety Mechanisms**
- Never deletes emails from personal domains (@gmail.com, @outlook.com)
- Skips deletion if fewer than 10 emails found (configurable threshold)
- Protects starred and important emails automatically
- Maintains a protected emails list for manual exceptions
- Logs all deletion activity for audit trails

**Smart Analysis**
- Scans your inbox to identify high-volume senders
- Filters out already-processed addresses
- Excludes personal email domains from suggestions
- Provides ready-to-use keyword lists

## Impact

After implementing this solution:
- Freed up 8+ GB of storage space
- Avoided Google One subscription costs (saves $20-100/year)
- Reduced inbox clutter from 50,000+ to manageable levels
- Established a repeatable maintenance workflow

## How It Works

The system uses two main scripts:

### 1. Gmail Analyzer (`gmail_analyzer.py`)
Scans your Gmail account and identifies senders with high email volumes. It automatically excludes:
- Personal email addresses (@gmail.com, @outlook.com)
- Previously processed senders (from history files)
- Protected addresses (from your configuration)

### 2. Gmail Cleaner (`gmail_cleaner.py`)
Deletes emails from specified senders with multiple safety checks:
- Opens separate browser tabs for each sender (batch processing)
- Checks total email count before deletion
- Skips if count is below safety threshold
- Cycles through tabs asynchronously for efficiency
- Logs all deletions and safe-skips to JSON files

## Installation

### Prerequisites
- Python 3.7+
- Chrome browser
- ChromeDriver (compatible with your Chrome version)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/shabul/gmail-storage-optimizer.git
cd gmail-storage-optimizer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure ChromeDriver is installed and in your PATH:
```bash
# macOS (using Homebrew)
brew install chromedriver

# Or download from: https://chromedriver.chromium.org/
```

## Usage

### First-Time Setup

1. **Create a Chrome profile** (the scripts will use this to maintain login):
   - The profile will be created automatically at `./chrome-profile/`
   - On first run, you'll need to log into Gmail manually
   - Subsequent runs will use the saved session

2. **Configure protected emails** (optional):
   - Edit `keywords.py`
   - Add any email addresses you want to permanently protect to the `protected_emails` list

### Finding Emails to Clean

Run the analyzer to identify high-volume senders:

```bash
python gmail_analyzer.py --pages 500
```

This will:
- Scan up to 500 pages of your Gmail
- Count emails from each sender
- Display senders with 10+ emails
- Exclude already-processed and personal addresses

Copy the output list to `keywords.py`.

### Cleaning Emails

Run the cleaner with your keyword list:

```bash
python gmail_cleaner.py
```

Or specify keywords directly:

```bash
python gmail_cleaner.py "noreply@example.com" "alerts@service.com"
```

The cleaner will:
- Process keywords in batches of 5 tabs
- Check email counts and skip if below threshold
- Delete emails iteratively until none remain
- Log all activity to `deleted_history.json` and `safe_not_deleted.json`

## Configuration

### Adjusting the Safety Threshold

Edit `gmail_cleaner.py` line 127:

```python
if total_count > 0 and total_count < 10:  # Change 10 to your preferred threshold
```

### Adjusting Batch Size

Edit `gmail_cleaner.py` line 30:

```python
BATCH_SIZE = 5  # Increase for faster processing, decrease for stability
```

### Adjusting Scan Depth

```bash
python gmail_analyzer.py --pages 1000  # Scan more pages for deeper analysis
```

## File Structure

```
gmail-storage-optimizer/
├── gmail_cleaner.py           # Main deletion script
├── gmail_analyzer.py          # Sender analysis script
├── keywords.py                # Email addresses to process
├── requirements.txt           # Python dependencies
├── deleted_history.json       # Log of successfully deleted keywords
├── safe_not_deleted.json      # Log of keywords skipped due to threshold
└── chrome-profile/            # Persistent Chrome session (auto-created)
```

## Safety Features Explained

### Personal Email Protection
The system automatically excludes `@gmail.com` and `@outlook.com` addresses to prevent accidental deletion of personal correspondence.

### Threshold Protection
If a sender has fewer than 10 emails (configurable), deletion is skipped. This prevents removing recent or important communication.

### Gmail Filters
All searches automatically exclude:
- Starred emails (`-is:starred`)
- Important emails (`-is:important`)

### Audit Trail
All actions are logged:
- `deleted_history.json`: Successfully processed senders
- `safe_not_deleted.json`: Senders skipped due to low count

### Rate Limiting Protection
Random delays (1-4 seconds) between actions prevent Google's anti-automation detection.

## Maintenance Workflow

For ongoing storage management:

1. **Monthly Analysis**: Run the analyzer to find new high-volume senders
2. **Review Suggestions**: Check the output and remove any you want to keep
3. **Run Cleaner**: Process the new keywords
4. **Monitor Storage**: Check your Google account storage dashboard

## Troubleshooting

### "Google Error 2" (Temporary Block)
- Wait 5-10 minutes before retrying
- The script includes random delays to minimize this
- Consider reducing `BATCH_SIZE` if it occurs frequently

### ChromeDriver Version Mismatch
```bash
# Check your Chrome version
google-chrome --version

# Download matching ChromeDriver from:
# https://chromedriver.chromium.org/downloads
```

### Login Session Expired
- Delete the `chrome-profile/` directory
- Run the script again and log in manually
- The session will be saved for future runs

## Contributing

Contributions are welcome. Please:
- Follow the existing code style
- Add comments for complex logic
- Test thoroughly before submitting PRs
- Update documentation for new features

## License

MIT License - feel free to use and modify for your needs.

## Disclaimer

This tool automates Gmail interactions using browser automation. Use responsibly and in accordance with Google's Terms of Service. The author is not responsible for any data loss or account issues resulting from use of this software.

Always review the keyword list before running the cleaner, and start with a small batch to verify behavior.

## Acknowledgments

Built out of necessity when facing the choice between paying for storage or spending hours manually deleting emails. This project proves that automation can solve real problems while maintaining safety and reliability.
