import os
import alpaca_trade_api as tradeapi
import yfinance as yf
import time
from datetime import datetime, timezone, timedelta
from pytz import timezone

# Load environment variables for Alpaca API
APIKEYID = os.getenv('APCA_API_KEY_ID')
APISECRETKEY = os.getenv('APCA_API_SECRET_KEY')
APIBASEURL = os.getenv('APCA_API_BASE_URL')

# Initialize the Alpaca API
api = tradeapi.REST(APIKEYID, APISECRETKEY, APIBASEURL)

# List of stock symbols (excluding 'SH')
stock_symbols = ['SPXL']


def get_current_price(symbol):
    stock_data = yf.Ticker(symbol)
    return round(stock_data.history(period='1d')['Close'].iloc[-1], 4)


def buy_stock_with_trailing_stop(symbol):
    try:
        # Get account information
        account_info = api.get_account()

        # Calculate the maximum number of whole shares that can be bought
        cash_available = float(account_info.cash)
        current_stock_price = get_current_price(symbol)
        max_shares = int(cash_available / current_stock_price)

        # Place a buy order with 0.25% trailing stop
        if max_shares > 0:
            buy_order = api.submit_order(
                symbol=symbol,
                qty=max_shares,
                side='buy',
                type='trailing_stop',
                trail_percent=0.25,  # Adjust as needed
                time_in_force='gtc'
            )
            print(f"Buy order placed for {max_shares} shares of {symbol} with 0.25% trailing stop.")

            # Wait for 2 minutes
            time.sleep(120)

            # Check day trade count
            day_trade_count = account_info.daytrade_count
            if day_trade_count < 3:
                # Generate trailing stop sell order with 0.25% trailing stop
                sell_order = api.submit_order(
                    symbol=symbol,
                    qty=max_shares,
                    side='sell',
                    type='trailing_stop',
                    trail_percent=0.25,
                    time_in_force='gtc'
                )
                print(f"Trailing stop sell order placed for {max_shares} shares of {symbol} with 0.25% trailing stop.")

    except Exception as e:
        print(f"Error: {str(e)}")


def is_market_open():
    eastern_timezone = timezone('US/Eastern')
    current_time = datetime.now(eastern_timezone)
    # buying after 10:02am Eastern Time because of the daily market price reversals near 10:00am - 10:15am Eastern time
    market_open_time = datetime(current_time.year, current_time.month, current_time.day, 10, 2, 0, 0, eastern_timezone)
    market_close_time = datetime(current_time.year, current_time.month, current_time.day, 16, 0, 0, 0, eastern_timezone)

    return current_time.weekday() < 5 and market_open_time <= current_time <= market_close_time


def get_next_market_open_time():
    eastern_timezone = timezone('US/Eastern')
    current_time = datetime.now(eastern_timezone)

    if current_time.weekday() == 4 and current_time.hour >= 16:
        # If today is Friday and after market close, add days until Monday
        next_market_open_time = datetime(current_time.year, current_time.month, current_time.day, 9, 30, 0, 0,
                                         eastern_timezone) + timedelta(days=(7 - current_time.weekday()) % 7)
    else:
        # Add days until the next market open
        next_market_open_time = datetime(current_time.year, current_time.month, current_time.day, 9, 30, 0, 0,
                                         eastern_timezone) + timedelta(days=(7 - current_time.weekday()) % 7)

    return next_market_open_time


# Execute the trading logic in a loop every 30 seconds
while True:
    if is_market_open():
        for symbol in stock_symbols:
            current_price = get_current_price(symbol)
            timestamp = datetime.now(timezone('US/Eastern')).strftime('%B %d, %Y %I:%M:%S %p')
            print(f"Current price of {symbol}: ${current_price:.4f}, Timestamp: {timestamp}")
            buy_stock_with_trailing_stop(symbol)
    else:
        next_market_open_time = get_next_market_open_time()
        print(f"Market is closed. Next market open time: {next_market_open_time.strftime('%B %d, %Y %I:%M:%S %p')}")

    next_run_time = datetime.now(timezone('US/Eastern')) + timedelta(seconds=30)
    print(f"Next run at {next_run_time.strftime('%B %d, %Y %I:%M:%S %p')}")
    time.sleep(30)  # Wait for 30 seconds before repeating the program
