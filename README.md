SOL Cryptocurrency Trading Bot
Project Description

This project is an automated cryptocurrency trading bot developed in Python.
The strategy combines trend detection, grid trading, and swing trading to adapt to different market conditions.
The bot connects to the exchange via API, executes trades automatically, and records trading data for further analysis and backtesting.

Strategy Logic

The trading strategy is based on the following indicators and concepts:

Trend detection using EMA (200)
RSI for overbought and oversold conditions
Bollinger Bands for entry timing
ADX for trend strength detection
ATR for stop-loss and trailing stop calculation
Grid trading for partial take-profit
Swing trading with trailing stop
Dynamic position sizing based on previous trade performance
Risk management and cooldown mechanism
Features
Automated trading via exchange API (CCXT)
Trend detection strategy
Grid trading strategy
Swing trading strategy
Dynamic position sizing
Stop-loss and trailing stop
Trade logging
Monthly trading data export to Excel
Telegram notification system
State persistence (bot can resume after restart)
Tools and Technologies
Python
CCXT
Pandas
Pandas-ta (Technical Indicators)
Asyncio
Excel (OpenPyXL)
Telegram Bot API
File Structure
sol_bot.py              # Main trading bot
sol_bot_state.json      # Bot state storage
sol_bot_log.log         # Trading log
*.xlsx                  # Monthly trading records
.env                    # API keys (not uploaded to GitHub)

How to Run
Install required packages:
pip install ccxt pandas pandas-ta openpyxl python-dotenv aiohttp
Create .env file:
MEXC_API_KEY=your_api_key
MEXC_SECRET_KEY=your_secret_key
TG_TOKEN=your_telegram_token
TG_CHAT_ID=your_chat_id
Run the bot:
python sol_bot.py
Research / Backtesting Purpose

The trading data is recorded and exported to Excel files for further statistical analysis, strategy evaluation, and backtesting.
This project can be considered a practical implementation of quantitative trading and financial data analysis.

Disclaimer

This project is for research and educational purposes only.
Trading cryptocurrencies involves risk, and the author is not responsible for any financial loss.
