import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import logging
import sys
import json
import os
import aiohttp
import time
import random
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# 0. 環境變數強制載入
# ==========================================
load_dotenv()
if not os.getenv('MEXC_API_KEY'):
    load_dotenv('key.env')

API_KEY = os.getenv('MEXC_API_KEY')
SECRET_KEY = os.getenv('MEXC_SECRET_KEY')
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

if not API_KEY or '你的' in API_KEY:
    print("❌ 錯誤：未讀取到有效的 API KEY，請檢查 .env 檔案")
    sys.exit(1)

# ==========================================
# 1. 系統設定
# ==========================================
SYMBOL = 'SOL/USDC'
TIMEFRAME = '15m'

# 基礎倉位 (剛啟動或虧損後使用)
BASE_RATIO = 0.50  
# 激進倉位 (賺錢後使用)
AGGRESSIVE_RATIO = 0.98

COOLDOWN_SECONDS = 300      
ADX_THRESHOLD = 25.0        

STATE_FILE = 'sol_bot_state.json'
LOG_FILE = 'sol_bot_log.log'

# ==========================================
# 2. 初始化 Logging
# ==========================================
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)

# ==========================================
# 3. Excel 記錄功能
# ==========================================
def save_to_excel(data_dict):
    try:
        current_month = datetime.now().strftime('%Y-%m')
        filename = f"{current_month}_trading_data.xlsx"
        new_row = pd.DataFrame([data_dict])
        
        if not os.path.exists(filename):
            new_row.to_excel(filename, index=False, engine='openpyxl')
        else:
            existing_df = pd.read_excel(filename, engine='openpyxl')
            combined_df = pd.concat([existing_df, new_row], ignore_index=True)
            combined_df.to_excel(filename, index=False, engine='openpyxl')
    except Exception as e:
        logging.error(f"Excel 存檔失敗: {e}")

# ==========================================
# 4. 狀態管理類別
# ==========================================
class BotState:
    def __init__(self):
        self.position_mode = None       
        self.entry_price = 0.0
        self.entry_quantity = 0.0
        self.grid_quantity = 0.0        
        self.fixed_sell_orders = []     
        self.stop_loss_price = 0.0      
        self.highest_price = 0.0        
        self.trailing_qty = 0.0         
        self.last_exit_time = 0.0       
        self.total_pnl = 0.0
        self.last_trade_result = 'loss' 
        self.win_count = 0
        self.loss_count = 0
        self.load()

    def save(self):
        temp_file = f"{STATE_FILE}.tmp"
        try:
            with open(temp_file, 'w') as f:
                json.dump(self.__dict__, f)
            os.replace(temp_file, STATE_FILE)
        except Exception as e:
            logging.error(f"存檔失敗: {e}")
    
    def load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f: self.__dict__.update(json.load(f))
            except: pass
            
    def reset(self):
        self.position_mode = None
        self.entry_price = 0.0
        self.entry_quantity = 0.0
        self.grid_quantity = 0.0
        self.fixed_sell_orders = []
        self.stop_loss_price = 0.0
        self.highest_price = 0.0
        self.trailing_qty = 0.0
        self.last_exit_time = time.time()
        self.save()

# ==========================================
# 5. 輔助函數
# ==========================================
async def send_telegram(msg):
    if not TG_TOKEN: return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {'chat_id': TG_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    logging.error(f"TG 發送失敗: {await resp.text()}")
    except Exception as e:
        logging.error(f"TG 連線錯誤: {e}")

def calculate_indicators(bars):
    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
    df['ema200'] = ta.ema(df['close'], length=200)
    bb = ta.bbands(df['close'], length=20, std=2)
    lower_col = [c for c in bb.columns if c.startswith('BBL')][0]
    upper_col = [c for c in bb.columns if c.startswith('BBU')][0]
    df['pct_b'] = (df['close'] - bb[lower_col]) / (bb[upper_col] - bb[lower_col])
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    if adx_df is not None and not adx_df.empty:
        df['adx'] = adx_df[adx_df.columns[0]]
    else:
        df['adx'] = 0.0 
    return df.iloc[-2]

async def wait_for_order_fill(exchange, order_id, symbol, timeout=60):
    for _ in range(timeout):
        try:
            order = await exchange.fetch_order(order_id, symbol)
            status = order['status']
            filled = float(order['filled'])
            if status == 'closed':
                return True, filled, float(order['average'] or order['price'])
            elif status == 'canceled':
                return False, filled, float(order['average'] or 0.0)
            await asyncio.sleep(1)
        except:
            await asyncio.sleep(1)
            
    try:
        await exchange.cancel_order(order_id, symbol)
        final = await exchange.fetch_order(order_id, symbol)
        filled = float(final['filled'])
        if filled > 0:
             return True, filled, float(final['average'] or final['price'])
    except: pass
    return False, 0.0, 0.0

def print_status(msg):
    sys.stdout.write(f"\r{datetime.now().strftime('%H:%M:%S')} | {msg}")
    sys.stdout.flush()

def print_event(msg):
    sys.stdout.write(f"\n{datetime.now().strftime('%H:%M:%S')} | {msg}\n")
    sys.stdout.flush()
    logging.info(msg)

# ==========================================
# 6. 主程式
# ==========================================
async def main():
    exchange = ccxt.mexc({
        'apiKey': API_KEY, 'secret': SECRET_KEY,
        'enableRateLimit': True,
        'timeout': 30000, 
        'options': {'defaultType': 'spot', 'adjustForTimeDifference': True}
    })
    
    state = BotState()
    start_msg = (f"🚀 <b>SOL 實戰版 啟動</b>\n"
                 f"策略: 贏了梭哈({AGGRESSIVE_RATIO*100}%) / 輸了減半({BASE_RATIO*100}%) \n"
                 f"當前狀態: {'🔥激進' if state.last_trade_result == 'win' else '🛡️保守'}模式 | 損益: {state.total_pnl:.2f}U")
    print_event(start_msg)
    await send_telegram(start_msg)

    last_excel_time = 0

    try:
        while True:
            try:
                # ------------------------------------------
                # 1. 數據獲取
                # ------------------------------------------
                try:
                    bars = await asyncio.wait_for(exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200), timeout=35)
                    ticker = await exchange.fetch_ticker(SYMBOL)
                    curr_realtime_price = float(ticker['last'])
                except Exception as net_err:
                    print_status(f"⚠️ 網路波動重試中... ({str(net_err)[:20]}...)")
                    await asyncio.sleep(5)
                    continue
                
                last_bar_time = int(bars[-1][0] / 1000)
                if int(time.time()) - last_bar_time > 1000:
                    print_status("⚠️ K線數據延遲...等待中")
                    await asyncio.sleep(10)
                    continue

                data = calculate_indicators(bars) 
                atr = data['atr']
                ema200 = data['ema200']
                adx = data['adx']
                
                # Excel 記錄
                if time.time() - last_excel_time > 900:
                    excel_data = {
                        'Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Price': curr_realtime_price,
                        'RSI': data['rsi'],
                        'ADX': adx,
                        'Pct_B': data['pct_b'],
                        'PnL': state.total_pnl,
                        'Mode': state.position_mode if state.position_mode else 'Scanning'
                    }
                    save_to_excel(excel_data)
                    last_excel_time = time.time()

                # ------------------------------------------
                # A. 持倉管理
                # ------------------------------------------
                if state.position_mode == 'holding':
                    if curr_realtime_price > state.highest_price:
                        state.highest_price = curr_realtime_price

                    if state.fixed_sell_orders and int(time.time()) % 30 == 0:
                        try:
                            open_orders = await exchange.fetch_open_orders(SYMBOL)
                            active_ids = [o['id'] for o in open_orders]
                            still_open = [oid for oid in state.fixed_sell_orders if oid in active_ids]
                            diff = len(state.fixed_sell_orders) - len(still_open)
                            
                            if diff > 0:
                                sold_qty = state.grid_quantity * diff
                                grid_profit = sold_qty * (curr_realtime_price - state.entry_price)
                                state.total_pnl += grid_profit
                                state.win_count += 1
                                state.last_trade_result = 'win'
                                
                                state.entry_quantity -= sold_qty
                                if state.entry_quantity < 0: state.entry_quantity = 0
                                
                                msg = f"💰 網格止盈! ({diff}單) 利潤: {grid_profit:.2f}U"
                                print_event(msg)
                                await send_telegram(msg)
                                state.fixed_sell_orders = still_open
                                state.save()
                                excel_data = {'Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Price': curr_realtime_price, 'Action': 'Grid Sell', 'Profit': grid_profit, 'Total_PnL': state.total_pnl}
                                save_to_excel(excel_data)
                        except: pass

                    trailing_stop_price = state.highest_price - (atr * 1.5)
                    effective_stop = max(state.stop_loss_price, trailing_stop_price)

                    status_msg = f"🛡️ 持倉中 💰損益:{state.total_pnl:.2f}U | 現價:{curr_realtime_price} | 止損:{effective_stop:.3f}"
                    print_status(status_msg)

                    if curr_realtime_price < effective_stop:
                        reason = "移動止盈" if effective_stop > state.stop_loss_price else "硬止損"
                        print_event(f"📉 {reason}觸發，執行平倉...")
                        
                        if state.fixed_sell_orders:
                            for oid in state.fixed_sell_orders:
                                try: await exchange.cancel_order(oid, SYMBOL)
                                except: pass
                            state.fixed_sell_orders = []
                            await asyncio.sleep(0.5)

                        qty = state.entry_quantity
                        if qty < 0.02: 
                             print_event(f"⚠️ 剩餘倉位過小 ({qty}) 無法出售，直接重置狀態")
                             state.reset()
                             continue

                        qty_str = exchange.amount_to_precision(SYMBOL, qty)
                        
                        try:
                            o = await exchange.create_order(SYMBOL, 'market', 'sell', qty_str)
                            s, sq, savg = await wait_for_order_fill(exchange, o['id'], SYMBOL)
                            if s:
                                pnl = (savg - state.entry_price) * sq
                                state.total_pnl += pnl
                                
                                if pnl > 0: 
                                    state.win_count += 1
                                    state.last_trade_result = 'win'
                                    res_str = "✅獲利"
                                else: 
                                    state.loss_count += 1
                                    state.last_trade_result = 'loss'
                                    res_str = "❌虧損"

                                print_event(f"🔴 {reason}出場 | 損益: {pnl:+.2f}U | 結果: {res_str}")
                                await send_telegram(f"🔴 <b>{reason}出場</b>\n損益: {pnl:+.2f}U\n判定: {res_str}")
                                
                                excel_data = {'Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Price': savg, 'Action': 'Exit', 'Profit': pnl, 'Total_PnL': state.total_pnl}
                                save_to_excel(excel_data)
                                state.reset()
                        except Exception as e:
                            if "amount" in str(e) and "precision" in str(e):
                                print_event(f"⚠️ 觸發最小下單限制 ({e})，強制重置")
                                state.reset()
                            else:
                                print_event(f"❌ 平倉失敗: {e}")

                # ------------------------------------------
                # 同步檢查
                # ------------------------------------------
                try:
                    bal = await exchange.fetch_balance()
                    coin_name = SYMBOL.split('/')[0]
                    real_sol_qty = float(bal['total'].get(coin_name, 0.0))
                    
                    real_pos_value = real_sol_qty * curr_realtime_price
                    HAS_REAL_POSITION = real_pos_value > 6.0
                    
                    if state.position_mode is None and HAS_REAL_POSITION:
                        print_event(f"🕵️ 偵測到手動買入! (持倉: {real_sol_qty:.3f} SOL)")
                        await send_telegram(f"🕵️ <b>偵測到外部建倉</b>\n機器人自動接管！")
                        state.position_mode = 'holding'
                        state.entry_quantity = real_sol_qty
                        state.entry_price = curr_realtime_price 
                        state.highest_price = curr_realtime_price
                        state.stop_loss_price = curr_realtime_price - (atr * 3.0) 
                        state.save()
                    
                    elif state.position_mode == 'holding' and not HAS_REAL_POSITION:
                        if not state.fixed_sell_orders:
                            print_event(f"🕵️ 偵測到倉位清空，切換回掃描")
                            await send_telegram("🕵️ <b>偵測到手動平倉</b>\n機器人重置狀態。")
                            state.reset()
                            continue 

                    elif state.position_mode == 'holding' and HAS_REAL_POSITION:
                        if abs(state.entry_quantity - real_sol_qty) / state.entry_quantity > 0.05:
                            print_event(f"🔄 修正持倉數量: {state.entry_quantity:.3f} -> {real_sol_qty:.3f}")
                            state.entry_quantity = real_sol_qty
                            state.save()

                except Exception as e:
                    pass

                # ------------------------------------------
                # B. 掃描模式 (🔥 V8.13 優化重點)
                # ------------------------------------------
                if state.position_mode is None:
                    if time.time() - state.last_exit_time < COOLDOWN_SECONDS:
                        remaining = int(COOLDOWN_SECONDS - (time.time() - state.last_exit_time))
                        print_status(f"❄️ 冷卻中... 💰損益:{state.total_pnl:.2f}U | 剩餘 {remaining} 秒")
                        await asyncio.sleep(1)
                        continue

                    current_ratio = AGGRESSIVE_RATIO if state.last_trade_result == 'win' else BASE_RATIO
                    mode_icon = "🔥激進" if state.last_trade_result == 'win' else "🛡️保守"

                    # --- 🔥 優化後的進場邏輯 ---
                    cond_trend_ma = data['close'] > ema200
                    cond_green = data['close'] > data['open']
                    
                    # 1. 暴跌過濾：如果 ADX > 45 且價格在均線下，代表空頭太強，禁止接刀
                    is_crashing = (adx > 45) and (data['close'] < ema200)
                    
                    # 2. RSI 條件 (逆勢更嚴格)
                    # 如果在均線上 (順勢) -> RSI < 40 就買
                    # 如果在均線下 (逆勢) -> RSI 必須 < 20 且不能是在暴跌中
                    if cond_trend_ma:
                        rsi_threshold = 40
                    else:
                        rsi_threshold = 20 # 逆勢時條件更嚴格
                        
                    cond_rsi = data['rsi'] < rsi_threshold
                    cond_bb = data['pct_b'] < 0.1 # 布林下軌

                    # 狀態顯示 (加入暴跌警告)
                    status_extra = "⚠️暴跌迴避中" if is_crashing else f"RSI:{data['rsi']:.1f}/{rsi_threshold}"
                    status_msg = f"🔎 掃描 💰損益:{state.total_pnl:.2f}U | {mode_icon}倉位:{int(current_ratio*100)}% | {status_extra}"
                    print_status(status_msg)

                    should_enter = False
                    
                    # 邏輯總結：
                    # 1. 必須收陽線 (cond_green)
                    # 2. 必須滿足 RSI 和 布林條件
                    # 3. 絕對不能是在「暴跌模式」 (not is_crashing)
                    if cond_rsi and cond_bb and cond_green and not is_crashing:
                        should_enter = True

                    if should_enter:
                        bal = await exchange.fetch_balance()
                        usdc_balance = float(bal['free'].get('USDC', 0.0))
                        
                        cost = usdc_balance * current_ratio
                        target_qty = cost / curr_realtime_price
                        
                        if cost < 5.1:
                            print_status(f"⚠️ 餘額不足 ({cost:.2f}U)，跳過")
                            await asyncio.sleep(60) 
                            continue

                        # 進場原因標記
                        if cond_trend_ma: reason_str = "🔥順勢回調"
                        else: reason_str = "⚠️超跌反彈"
                        
                        msg = f"⚡ 觸發買入! ({reason_str}) | {mode_icon}投入: {cost:.2f}U ({int(current_ratio*100)}%)"
                        print_event(msg)
                        await send_telegram(msg)
                        
                        sl_dist = atr * 2.5
                        buy_p = curr_realtime_price * 1.003
                        
                        try:
                            o = await exchange.create_order(SYMBOL, 'limit', 'buy', 
                                                          exchange.amount_to_precision(SYMBOL, target_qty), 
                                                          exchange.price_to_precision(SYMBOL, buy_p))
                            s, fq, avg = await wait_for_order_fill(exchange, o['id'], SYMBOL)
                            
                            if s and fq > 0:
                                state.position_mode = 'holding'
                                state.entry_price = avg
                                state.entry_quantity = fq
                                state.stop_loss_price = avg - sl_dist
                                state.highest_price = avg
                                
                                print_event(f"🟢 成交 | 均價: {avg} | 止損: {state.stop_loss_price:.3f}")
                                await send_telegram(f"🟢 <b>成交</b>\n均價: {avg}\n止損: {state.stop_loss_price:.3f}")
                                excel_data = {'Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Price': avg, 'Action': 'Buy', 'Profit': 0, 'Total_PnL': state.total_pnl}
                                save_to_excel(excel_data)

                                # 網格掛單
                                grid_levels = 3
                                if (fq * avg) / grid_levels > 6.0:
                                    spacing = atr * 1.2
                                    total_precise = float(exchange.amount_to_precision(SYMBOL, fq))
                                    grid_qty = float(exchange.amount_to_precision(SYMBOL, total_precise / grid_levels))
                                    state.grid_quantity = grid_qty
                                    
                                    f_orders = []
                                    used_qty = 0.0
                                    for i in range(1, grid_levels):
                                        tp = avg + (spacing * i)
                                        try:
                                            o = await exchange.create_order(SYMBOL, 'limit', 'sell', 
                                                                          exchange.amount_to_precision(SYMBOL, grid_qty), 
                                                                          exchange.price_to_precision(SYMBOL, tp))
                                            f_orders.append(o['id'])
                                            used_qty += grid_qty
                                        except: pass
                                    
                                    state.fixed_sell_orders = f_orders
                                    state.trailing_qty = float(exchange.amount_to_precision(SYMBOL, total_precise - used_qty))
                                else:
                                    state.trailing_qty = fq
                                    state.grid_quantity = 0.0
                                state.save()
                        except Exception as e:
                            print_event(f"❌ 下單失敗: {e}")
                            await asyncio.sleep(60) 

            except Exception as e:
                if "GET" not in str(e): 
                    print_event(f"系統錯誤: {e}")
                await asyncio.sleep(5)
            
            base_sleep = 5 if state.position_mode == 'holding' else 8
            random_sleep = base_sleep + random.uniform(0, 4)
            await asyncio.sleep(random_sleep)

    except KeyboardInterrupt:
        print_event("程式手動停止")
    finally:
        await exchange.close()

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass