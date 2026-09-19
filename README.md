# Daily Weather Email Automation 🌦️

An automated Python system that fetches real-time weather forecasts and sends a daily summary email with rain alerts using Gmail SMTP and Open-Meteo API.

---

## 🚀 Features

- **No API Key Required**: Powered by [Open-Meteo API](https://open-meteo.com/), completely free with open access.
- **Detailed Metrics**:
  - Temperature & Apparent ("Feels-like") Temperature (°C)
  - Weather Condition & WMO Description
  - Relative Humidity (%)
  - Rain Probability / Precipitation Chance (%)
  - Wind Speed (km/h)
- **Smart Umbrella Alert**: Automatically alerts you when the rain probability exceeds 50%.
- **Automated Cloud Scheduling**: Pre-configured [GitHub Actions Workflow](.github/workflows/daily_weather.yml) runs every day at 8:00 AM UTC.
- **On-Demand Execution**: Run anytime manually using CLI flag `--now`.

---

## 📁 Project Structure

```text
├── .github/
│   └── workflows/
│       └── daily_weather.yml    # GitHub Actions cron schedule
├── Agent.py                     # Main weather & email automation script
├── requirements.txt             # Project dependencies
├── .gitignore                   # Ignored files
└── README.md                    # Project documentation
```

---

## 🛠️ Getting Started (Local Setup)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Immediately (Test Run)
To trigger an immediate weather fetch and send a test email:
```bash
python Agent.py --now
```

### 3. Run Local Daily Scheduler
To keep the script running in the background and send emails daily at 8:00 AM:
```bash
python Agent.py
```

---

## ⚙️ Configuration & Environment Variables

You can configure settings via environment variables or use the built-in defaults in `Agent.py`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `WEATHER_CITY` | City to fetch weather for | `London` |
| `WEATHER_COUNTRY_CODE` | ISO country code | `GB` |
| `SMTP_SERVER` | SMTP host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_EMAIL` | Sender Gmail address | Configured in `Agent.py` |
| `SMTP_PASSWORD` | 16-character Gmail App Password | Configured in `Agent.py` |
| `RECEIVER_EMAIL` | Recipient email address | Configured in `Agent.py` |
| `RAIN_THRESHOLD_PERCENT` | Rain alert threshold | `50` |

---

## ☁️ GitHub Actions Automation

The workflow in `.github/workflows/daily_weather.yml` will automatically:
1. Trigger daily at `08:00 UTC` (`0 8 * * *`).
2. Run on-demand whenever you click **Run workflow** in the GitHub **Actions** tab.
