import os
import ccxt
import pandas as pd
import pandas_ta as ta
import time
from configparser import ConfigParser
from line_notify import LineNotify


dbconf = ConfigParser()
dbconf.read_file(open('config.ini'))

API_KEY = dbconf.get('Config','API_KEY')
API_SECRET = dbconf.get('Config','API_SECRET')
ACCESS_TOKEN = dbconf.get('Config','ACCESS_TOKEN')

symbolName = dbconf.get('Setting','symbolName').split(",")
leverage = dbconf.get('Setting','leverage').split(",")
TF = dbconf.get('Setting','TF')
fastEMAValue = dbconf.get('Setting','fastEMAValue')
slowEMAValue = dbconf.get('Setting','slowEMAValue')
signal_length = dbconf.get('Setting','signal')
cost = dbconf.get('Setting','costpercent')

tpslmode = dbconf.get('TPSL','mode')
tp = dbconf.get('TPSL','tppercent')
sl = dbconf.get('TPSL','slpercent')

TRAILING_STOPmode = dbconf.get('TrailingStop','TLmode')
callback = dbconf.get('TrailingStop','callbackrate')
tpTL = dbconf.get('TrailingStop','Activationprice')
notify = LineNotify(ACCESS_TOKEN)

mes="ยินดีต้อนรับเข้าสู่\n~Binance Future MACD 1.0.0 Bot~"+"\n\n🧭 === Setting === 🧭\n\nAsset : "+str(symbolName)+"\nLeverage : "+str(leverage)+"\nTime Frame : "+TF+"\nTPSL Mode : "+str(tpslmode)
notify.send(mes)

longposition = False
shortposition = False
inposition = False
signalupcross = False
signaldowncross = False
amount = 0
ROE = 0

exchange = ccxt.binance({
"apiKey": API_KEY,
"secret": API_SECRET,

'options': {
'defaultType': 'future'
},
'enableRateLimit': True
})

while True:
    n = 0
    H = 60*6
    while (n < H):
        try:
            balance = exchange.fetch_balance()
            free_balance = exchange.fetch_free_balance()      
            positions = balance['info']['positions']
            print ("Bot MACD 1.0.0\n====================")
            for i in range(len(symbolName)):
                symbolNamei = symbolName[i]
                newSymboli = symbolName[i]+"USDT"
                symboli = symbolName[i] + "/USDT"
                leveragei=leverage[i]
                current_positions = [position for position in positions if float(position['positionAmt']) != 0 and position['symbol'] == newSymboli]
                position_info = pd.DataFrame(current_positions, columns=["symbol", "entryPrice", "unrealizedProfit", "isolatedWallet", "positionAmt", "positionSide","initialMargin"])
                #print(newSymboli)
                
            #คำสั่งเซท leverage
                exchange.load_markets()
                market = exchange.markets[symboli]
                exchange.fapiPrivate_post_leverage({"symbol": market['id'],"leverage": leveragei,}) 
                
                if not position_info.empty and position_info["positionAmt"][len(position_info.index) - 1] != 0:
                    inposition = True
                else: 
                    inposition = False
                    shortposition = False
                    longposition = False
                
            # Check Long position?
                if inposition and float(position_info["positionAmt"][len(position_info.index) - 1]) > 0:
                	   	longposition = True
                	   	shortposition = False
            # Check Short position?
                if inposition and float(position_info["positionAmt"][len(position_info.index) - 1]) < 0:
                	   	shortposition = True
                	   	longposition = False
                
            # LOAD BARS                
                bars = exchange.fetch_ohlcv(symboli, timeframe=TF, since = None, limit = 300)
                df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

            # RSI  
                emafast = ta.ema(df["close"],int(fastEMAValue))
                emaslow = ta.ema(df["close"],int(slowEMAValue))
                
                macd = emafast - emaslow
                #print(macd)
                
                macd1 = macd.iloc[-2]
                macd2 = macd.iloc[-3]
                
                signal = ta.ema(macd,int(signal_length))
                #print(signal)
                
                signal1 = signal.iloc[-2]
                signal2 = signal.iloc[-3]
                
                
                
            #เงื่อนไขบอกว่าจุดตัด
                #ตัดขึ้น                               
                if macd2 < signal2 and macd1 >= signal1:
                	signalupcross = True
                else: 
                	signaldowncross = False
                #ตัดลง
                if macd2 > signal2 and macd1 <= signal1:
                	signaldowncross = True
                else: 
                	signalupcross = False
                
            # LONG ENTER
                def longEnter(amount):
                    order = exchange.create_market_buy_order(newSymboli, amount)
                                       
            # LONG EXIT
                def longExit():
                    order = exchange.create_market_sell_order(newSymboli,float(position_info["positionAmt"][len(position_info.index) - 1]), {"reduceOnly": True})
                    
            # SHORT ENTER
                def shortEnter(amount):
                    order = exchange.create_market_sell_order(newSymboli, amount)
                                        
            # SHORT EXIT
                def shortExit():
                    order = exchange.create_market_buy_order(newSymboli, (float(position_info["positionAmt"][len(position_info.index) - 1]) * -1), {"reduceOnly": True})


              	   
             # BULL EVENT       
                if signalupcross == True and macd1 >= signal1 and longposition == False:
                    if shortposition:
                        print(str(newSymboli)+"\nStatus : Close SHORT PROCESSING...")     	       		
                        shortExit()
                    amount = (((float(free_balance["USDT"]) / 100 ) * float(cost)) * float(leveragei)) / float(df["close"][len(df.index) - 2])
                    print(str(newSymboli)+"\nStatus : LONG ENTERING PROCESSING...")
                    #longEnter(amount)
                    message ="\n"+ newSymboli +" "+str(leveragei)+" x"+ "\nสถานะ : LONG RSI ↗️\n" + "ราคา : "+str(round(df["close"][len(df.index) - 1],5))+" USDT"+"\nจำนวน : "+str(round(amount,2))+" "+str(symbolNamei)+" / "+str(round((float(amount)*float(df["close"][len(df.index) - 1]))/float(leveragei),2))+" USDT\nMACD cross :"+str(round(macd1,2))+" > "+str(round(signal1,2))+"\n\n💰ยอดเงินคงเหลือ : " + str(round(balance['total']["USDT"],2))+" USDT"
                    notify.send(message)

                    
                    
                    
            # BEAR EVENT    
                if signaldowncross == True and macd1 <= signal1 and shortposition == False:
                    if longposition:
                        print(str(newSymboli)+"\nStatus : Close LONG PROCESSING...")
                        longExit()
                    amount = (((float(free_balance["USDT"]) / 100 ) * float(cost)) * float(leveragei)) / float(df["close"][len(df.index) -2])
                    print (str(newSymboli)+"\nStatus : SHORT ENTERING PROCESSING....")
                    #shortEnter(amount)
                    message ="\n"+ newSymboli +" "+str(leveragei)+" x"+ "\nสถานะ : SHORT RSI ↘️\n" + "ราคา : "+str(round(df["close"][len(df.index) - 1],5))+" USDT"+"\nจำนวน : "+str(round(amount,2))+" "+str(symbolNamei)+" / "+str(round((float(amount)*float(df["close"][len(df.index) - 1]))/float(leveragei),2))+" USDT\nMACD cross :"+str(round(macd1,2))+" < "+str(round(signal1,2))+"\n\n💰ยอดเงินคงเหลือ : " + str(round(balance['total']["USDT"],2))+" USDT"
                    notify.send(message)


                if tpslmode == 'on' :
                    if longposition or shortposition:
                        ROE=(float(position_info["unrealizedProfit"][len(position_info.index) - 1])*100)/float(position_info["initialMargin"][len(position_info.index) - 1])
                        TP=float(tp)*float(leveragei)
                        #print(TP)
                        SL=-(float(sl)*float(leveragei))
                        #print(SL)                       
                        if signalupcross == False and TP != 0 and ROE >= TP:
                            if longposition:
                                print(str(newSymboli)+"\nStatus : LONG TAKE PROFIT PROCESSING...")
                                longExit()
                                message = "\n"+ newSymboli +" "+str(leveragei)+" x"+ "\nสถานะ : Long TP 😆\n" + "ราคา : "+str(round(df["close"][len(df.index) - 1],5))+" USDT"+"\nROE : "+str(round(ROE,2))+" %\n\n💰ยอดเงินคงเหลือ : " + str(round(balance['total']["USDT"],2))+" USDT"
                                notify.send(message)
                            if shortposition:
                                print(str(newSymboli)+"\nStatus : SHORT TAKE PROFIT PROCESSING...")
                                shortExit()
                                message = "\n"+ newSymboli +" "+str(leveragei)+" x"+ "\nสถานะ : Short TP 😆\n" + "ราคา : "+str(round(df["close"][len(df.index) - 1],5))+" USDT"+"\nROE : "+str(round(ROE,2))+" %\n\n💰ยอดเงินคงเหลือ : " + str(round(balance['total']["USDT"],2))+" USDT"
                                notify.send(message)                             
                        if signaldowncross == False and SL != 0 and ROE <= SL :
                            if longposition:
                                print(str(newSymboli)+"\nStatus : LONG STOP LOSS PROCESSING...")
                                longExit()
                                message = "\n"+ newSymboli +" "+str(leveragei)+" x"+ "\nสถานะ : Long SL 😭\n" + "ราคา : "+str(round(df["close"][len(df.index) - 1],5))+" USDT"+"\nROE : "+str(round(ROE,2))+" %\n\n💰ยอดเงินคงเหลือ : " + str(round(balance['total']["USDT"],2))+" USDT"
                                notify.send(message)
                            if shortposition:
                                print(str(newSymboli)+"\nStatus : SHORT STOP LOSS PROCESSING...")
                                shortExit()
                                message = "\n"+ newSymboli +" "+str(leveragei)+" x"+ "\nสถานะ : Short SL 😭\n" + "ราคา : "+str(round(df["close"][len(df.index) - 1],5))+" USDT"+"\nROE : "+str(round(ROE,2))+" %\n\n💰ยอดเงินคงเหลือ : " + str(round(balance['total']["USDT"],2))+" USDT"
                                notify.send(message)

                if inposition == False:
                    print(str(newSymboli)+"\nStatus : Wait Position ...")

                if shortposition:
                    print(str(newSymboli)+"\nStatus : Short Position")
        		 		
                if longposition:
                    print(str(newSymboli)+"\nStatus : Long Position")
             
                print("====================")
                
            n += 1
            time.sleep(10)
# posix is os name for linux or mac
            if(os.name == 'posix'):
                os.system('clear')
# else screen will be cleared for windows
            else:
                os.system('cls')
           
           
        except ccxt.BaseError as Error:
            print ("[ERROR] ", Error )
            continue
    mes="\nBot MACD running\n💰ยอดเงินคงเหลือ : " + str(round(balance['total']["USDT"],2))+" USDT"
    notify.send(mes)
