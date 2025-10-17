#  Docker Setup Guide - Limmatwelle PDF Scraper

##  Prerequisites

- Docker installed (version 20.10+)
- Docker Compose installed (version 2.0+)
- At least 2GB free disk space

---

##  Quick Start

### **Option 1: Using Docker Compose**

```bash
# 1. Build the image
docker-compose build

# 2. Run the scraper
docker-compose up

# 3. Results will be in ./output/ directory
ls output/
```

### **Option 2: Using Docker directly**

```bash
# 1. Build the image
docker build -t limmatwelle-scraper .

# 2. Run the scraper
docker run --rm \
  -v $(pwd)/output:/app/downloads \
  limmatwelle-scraper

# 3. Check results
ls output/
```

---

## 📂 Project Structure

```
.
├── Dockerfile                          # Docker image definition
├── docker-compose.yml                  # Docker Compose configuration
├── requirements.txt                    # Python dependencies
├── limmatwelle_scraper_selenium.py     # Main scraper script
├── .dockerignore                       # Files to exclude from build
├── output/                             # Output directory (created automatically)
│   ├── limmatwelle_22_mai.pdf          # Downloaded PDF
│   ├── page_12_13_raw.txt              # Extracted text
│   └── baugesuch_output.json           # Final JSON output
└── README.md                           # This file
```

---

##  Configuration

To change the target date or pages, **edit the script directly** before building:

### **Edit limmatwelle_scraper_selenium.py:**

```python
# Line ~18-21
EPAPER_URL = "https://www.limmatwelle.ch/e-paper"
TARGET_DATE = "22. Mai"        # ← Change this
TARGET_PAGES = [12, 13]         # ← Change this
DOWNLOAD_DIR = os.path.abspath("./downloads")
PDF_FILENAME = "limmatwelle_22_mai.pdf"
```

### **Example: Change to different date**

```python
TARGET_DATE = "15. Juni"        # New date
TARGET_PAGES = [10, 11]         # Different pages
```

Then rebuild:
```bash
docker-compose build
docker-compose up
```

---

##  Output Files

After running, you'll find these files in `./output/`:

1. **`limmatwelle_22_mai.pdf`** - Downloaded PDF from issuu
2. **`page_12_13_raw.txt`** - Raw extracted text from pages 12-13
3. **`baugesuch_output.json`** - Parsed Baugesuch data in JSON format

### **Example JSON Output:**

```json
[
  {
    "Baugesuch_Nr": "202536",
    "Bauherrschaft": "Ortsbürgergemeinde,Würenlos,Schulstrasse26,5436Würenlos",
    "Bauvorhaben": "Dachsanierung",
    "Lage": "Parzelle4885(Plan25),Forsthouse'Tägerhard'",
    "Zone": "AusserhalbBauzone-Wald",
    "Zusatzgesuch": "DepartementBau,VerkehrundUmwelt",
    "others": "Gesuchsauflage vom 23. Mai bis 23. Juni 2025..."
  }
]
```

---

##  Troubleshooting

### **Error: Chrome not found**

```bash
# Rebuild the image
docker-compose build --no-cache
```

### **Error: Permission denied on output directory**

```bash
# Fix permissions
sudo chown -R $USER:$USER output/
chmod 755 output/
```

### **Error: Container exits immediately**

```bash
# Check logs
docker-compose logs

# Or run interactively
docker-compose run --rm scraper bash
```

### **Error: Download failed / Cookie banner issue**

The script already handles cookie banners automatically. If it still fails:

1. Check if issuu.com changed their UI
2. View browser logs: `docker-compose logs scraper`
3. The PDF might already exist in `./output/` from previous run

---

##  Development & Debugging

### **Interactive Mode**

Run the container interactively to debug:

```bash
# Using docker-compose
docker-compose run --rm scraper bash

# Inside container, test:
python limmatwelle_scraper_selenium.py

# Or test Chrome:
google-chrome --version
```

### **View Logs in Real-time**

```bash
docker-compose logs -f scraper
```

### **Check Chrome Version**

```bash
docker run --rm limmatwelle-scraper google-chrome --version
```

### **Test Without Headless Mode**

Edit `limmatwelle_scraper_selenium.py` line ~44:

```python
# Comment out headless mode to see browser
# chrome_options.add_argument('--headless')
```

Then rebuild and run.

---

##  Deployment to Production Server

### **1. Copy files to server**

```bash
# On local machine
scp -r ./* user@server:/path/to/app/

# Or use git
git clone https://github.com/shandraklr/web-scraping-limmatwelle-issuu.git
cd https://github.com/shandraklr/web-scraping-limmatwelle-issuu.git
```

### **2. On server, build and run**

```bash
cd /path/to/app/

# Build
docker-compose build

# Run (detached mode)
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

### **3. Schedule with Cron**

```bash
# Edit crontab
crontab -e

# Add this line to run every day at 9 AM
0 9 * * * cd /path/to/app && docker-compose run --rm scraper >> /var/log/scraper.log 2>&1
```

---

4. **Limit resources:**

```yaml
# Already in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

---

##  Advanced Usage

### **Modify Target Date/Pages**

**Before building**, edit `limmatwelle_scraper_selenium.py`:

```python
TARGET_DATE = "15. Juni"     # Change date
TARGET_PAGES = [10, 11]      # Change pages
```

Then:
```bash
docker-compose build
docker-compose up
```

---

## Support & Debugging Commands

### **Common Debug Commands**

```bash
# Check if container is running
docker ps

# View all containers (including stopped)
docker ps -a

# Check container logs
docker-compose logs scraper

# Follow logs in real-time
docker-compose logs -f scraper

# Inspect container
docker inspect limmatwelle-scraper

# Check disk space
docker system df

# Clean up unused resources
docker system prune
```

### **Test Individual Components**

```bash
# Test Chrome
docker run --rm limmatwelle-scraper google-chrome --version

# Test Python
docker run --rm limmatwelle-scraper python --version

# Test Selenium import
docker run --rm limmatwelle-scraper python -c "from selenium import webdriver; print('OK')"

# Test pypdf import
docker run --rm limmatwelle-scraper python -c "from pypdf import PdfReader; print('OK')"
```

---

## Configuration Reference

### **Hard-coded Configuration (in script)**

| Variable | Default | Location | Description |
|----------|---------|----------|-------------|
| `EPAPER_URL` | `https://www.limmatwelle.ch/e-paper` | Line 18 | E-paper archive URL |
| `TARGET_DATE` | `22. Mai` | Line 19 | Target edition date |
| `TARGET_PAGES` | `[12, 13]` | Line 20 | Pages to extract |
| `DOWNLOAD_DIR` | `./downloads` | Line 21 | Download directory |
| `PDF_FILENAME` | `limmatwelle_22_mai.pdf` | Line 22 | Output filename |

### **Docker Configuration (in docker-compose.yml)**

| Setting | Default | Description |
|---------|---------|-------------|
| `cpus` | 2 | CPU limit |
| `memory` | 2G | Memory limit |
| `restart` | unless-stopped | Restart policy |


---

## 💡 Tips & Tricks

### **Tip 1: Keep Container Running for Debugging**

```bash
# Start container with bash instead of running script
docker-compose run --rm scraper bash

# Inside container:
ls -la
python limmatwelle_scraper_selenium.py
exit
```

### **Tip 2: Quick Rebuild After Code Changes**

```bash
# Only rebuild changed layers
docker-compose build

# Full rebuild (no cache)
docker-compose build --no-cache
```

### **Tip 3: Save Docker Image**

```bash
# Save image to file
docker save limmatwelle-scraper:latest | gzip > limmatwelle-scraper.tar.gz

# Load on another machine
gunzip -c limmatwelle-scraper.tar.gz | docker load
```

### **Tip 4: Monitor Resource Usage**

```bash
# Check CPU/Memory usage
docker stats limmatwelle-scraper

# Check logs size
du -sh /var/lib/docker/containers/*
```

---

##  Learning Resources

**Docker:**
- https://docs.docker.com/get-started/

**Selenium:**
- https://selenium-python.readthedocs.io/

**Chrome Headless:**
- https://developers.google.com/web/updates/2017/04/headless-chrome

---

##  Output Files

After running, you'll find these files in `./output/`:

1. **`limmatwelle_22_mai.pdf`** - Downloaded PDF from issuu
2. **`page_12_13_raw.txt`** - Raw extracted text from pages 12-13
3. **`baugesuch_output.json`** - Parsed Baugesuch data in JSON format

### **Example JSON Output:**

```json
[
  {
    "Baugesuch_Nr": "202536",
    "Bauherrschaft": "Ortsbürgergemeinde,Würenlos,Schulstrasse26,5436Würenlos",
    "Bauvorhaben": "Dachsanierung",
    "Lage": "Parzelle4885(Plan25),Forsthouse'Tägerhard'",
    "Zone": "AusserhalbBauzone-Wald",
    "Zusatzgesuch": "DepartementBau,VerkehrundUmwelt",
    "others": "Gesuchsauflage vom 23. Mai bis 23. Juni 2025..."
  }
]
```

---
```