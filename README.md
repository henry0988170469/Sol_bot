🚀 SOL Cryptocurrency Trading Bot
📝 Project Description
This project is an automated cryptocurrency trading bot developed in Python. The strategy combines trend detection, grid trading, and swing trading to adapt to various market conditions.

The bot connects to exchanges via the CCXT API, executes trades automatically, and logs comprehensive trading data for further statistical analysis and backtesting. This implementation serves as a practical tool for quantitative trading and financial data exploration.

🧠 Strategy Logic
The trading strategy integrates several technical indicators and risk management concepts:

Trend Detection: Utilizes EMA (200) to identify the long-term market direction.

Momentum & Volatility:

RSI: Identifies overbought and oversold conditions.

Bollinger Bands: Optimizes entry timing based on price volatility.

ADX: Measures the strength of the current trend.

Risk Management:

ATR: Calculates precise stop-loss and trailing stop levels.

Dynamic Position Sizing: Adjusts trade size based on previous performance.

Cooldown Mechanism: Prevents over-trading during high-volatility or losing streaks.

Execution Models:

Grid Trading: Facilitates partial take-profits during sideways movement.

Swing Trading: Captures larger trend moves with trailing stops.

✨ Features
🤖 Automated Trading: Seamless integration via exchange APIs (CCXT).

📈 Hybrid Strategy: Combines Trend, Grid, and Swing trading models.

🛡️ Advanced Risk Control: Dynamic sizing, ATR-based stops, and cooldown periods.

📊 Data Analytics: Automatic monthly export of trading records to Excel.

📝 Robust Logging: Detailed logging of every trade and state change.

🔔 Notifications: Real-time updates via the Telegram Bot API.

💾 State Persistence: Capability to resume operations instantly after a restart.

🛠 Tools and Technologies
Language: Python

Exchange Connectivity: CCXT

Data Processing: Pandas

Technical Analysis: Pandas-ta

Asynchronous I/O: Asyncio

Excel Reporting: OpenPyXL

Communication: Telegram Bot API

📂 File Structure
Plaintext
.
├── sol_bot.py           # Main trading bot engine
├── sol_bot_state.json   # JSON storage for state persistence
├── sol_bot_log.log      # Detailed execution logs
├── *.xlsx               # Auto-generated monthly trading records
├── .env                 # API keys and sensitive configuration (Hidden)
└── README.md            # Project documentation
🚀 How to Run
1. Install required packages
Ensure you have Python installed, then run:

Bash
pip install ccxt pandas pandas-ta openpyxl python-dotenv aiohttp
2. Configure Environment Variables
Create a .env file in the root directory and add your credentials:

程式碼片段
MEXC_API_KEY=your_api_key
MEXC_SECRET_KEY=your_secret_key
TG_TOKEN=your_telegram_token
TG_CHAT_ID=your_chat_id
3. Start the Bot
Bash
python sol_bot.py
📊 Research / Backtesting Purpose
This project is designed with a strong focus on Quantitative Analysis. Trading data is recorded and exported to Excel to facilitate:

In-depth statistical analysis of trade performance.

Strategy evaluation and parameter optimization.

Refining backtesting models with real-world execution data.

⚠️ Disclaimer
This project is for research and educational purposes only. Trading cryptocurrencies involves significant risk. The author is not responsible for any financial losses incurred through the use of this software. Always trade responsibly.
