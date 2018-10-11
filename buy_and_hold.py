from rqalpha.api import *
import talib
import numpy as np
from rqalpha.utils.datetime_func import convert_date_to_int, convert_int_to_date
import pandas as pd
class DailyStockStatus():
    def __init__(self,StockID,GoldenPrice):
        self.StockID = 0
        self.BottomDays = 0
        self.VolumeBoosted = False
        self.GoldenPrice = GoldenPrice
        self.BoostRate = 0
        self.MinPrice = 0
        self.TrendRevered = False
        self.DateTimeMax = 0
        self.DateTimeMin = 0
        self.MaxPrice = 0
        self.ReversedHight = 0
        self.DateRevserdHight = 0
        self.ReversedStockPeriod = 8
        self.DecreasedRatio = 0
        self.ReversedRatio = 0
    def tostr(self):
        return ("BottomDays = "+str(self.BottomDays)+", VolumeBoosted = "+str(self.VolumeBoosted))

class SelfSelectedPool():
    def __init__(self):
        self.stock_pool = {}

    def update(self, context):
        for stock in context.stocks:
            if stock in self.stock_pool:
                #忽略已经在股票池中的股票
                continue
            # 读取历史数据
            prices = history_bars(stock, context.DECLINE_TIME_PERIOD + 1, '1d',None,True,False,'post') #not defined?
            if prices.size < 35:
                continue
            #判断股价当天是否出现最小值
            stock_low = prices['low']
            MinPrice = np.min(stock_low)
            MinPrice_index = stock_low.argmin()
            date_time = prices['datetime']
            DateTimeMin = date_time[MinPrice_index]
            dt = np.uint64(convert_date_to_int(context.now))
            if dt != DateTimeMin:
                continue
            # 如果跌到黄金分割位则加入stock pool
            stock_high = prices['high']
            MaxPrice = np.max(stock_high)

            golden_price = MaxPrice * context.GOLDEN_RATIO
            close_price = prices[-1]['close']
            if not stock_price_equal(MinPrice, golden_price, context.UNCERTAINTY_RATE):
                continue
            self.stock_pool[stock] = DailyStockStatus(stock[0:6],golden_price)
            self.stock_pool[stock].BottomDays = 1
            self.stock_pool[stock].DateTimeMin = DateTimeMin
            MaxPrice_index = np.where(stock_high == MaxPrice)[-1][-1]
            self.stock_pool[stock].DateTimeMax = date_time[MaxPrice_index]
            self.stock_pool[stock].MinPrice = MinPrice
            self.stock_pool[stock].MaxPrice = MaxPrice
            #logger.info(stock + " added to self selected stock pool")
        #每天更新加入到了股票池里面的每只股票的状态
        for stock in list(self.stock_pool.keys()):
            # 读取历史数据
            prices = prices = history_bars(stock, context.DECLINE_TIME_PERIOD + 1, '1d',None,True,False,'post')
            stock_status = self.stock_pool[stock]

            #更新底部驻留天数
            self.stock_pool[stock].BottomDays += 1
            # 判断底部成交量是否放大2倍
            if stock_status.VolumeBoosted == False:
                stock_volume = prices['volume']
                today_volume = stock_volume[-1]
                today_volume_avr = talib.SMA(stock_volume, 5)
                today_volume_avr = today_volume_avr[-1]
                if today_volume > (today_volume_avr * 2):
                    self.stock_pool[stock].VolumeBoosted = True
                    logger.info(stock + " bottom boosted 2 times")
                    BoostRate = today_volume/today_volume_avr
                    self.stock_pool[stock].BoostRate = BoostRate

            high_price = prices[-1]['high']
            low_price = prices[-1]['low']
            if low_price < self.stock_pool[stock].MinPrice:
                # 股价创出新低，更新股票最低价
                self.stock_pool[stock].MinPrice = low_price
                # del self.stock_pool[stock]
                dt = np.uint64(convert_date_to_int(context.now))
                self.stock_pool[stock].DateTimeMin = dt
                logger.info(stock + " falling with new lowest price")

            if (high_price > (self.stock_pool[stock].MinPrice*1.2)) and (self.stock_pool[stock].TrendRevered == False):
                # 股票从底部最低点增长20%，趋势可能发生反转
                self.stock_pool[stock].TrendRevered = True
                self.stock_pool[stock].ReversedHight = high_price
                self.stock_pool[stock].DateRevserdHight = np.uint64(convert_date_to_int(context.now))
                #logger.info(stock + " trend posible reversed"+ " DateTimeMax: "+str(self.stock_pool[stock].DateTimeMax)+ " DateTimeMin: "+str(self.stock_pool[stock].DateTimeMin)+" MaxPrice:"+str(self.stock_pool[stock].MaxPrice)+" MinPrice:"+str(self.stock_pool[stock].MinPrice)+" decresed: "+str(((self.stock_pool[stock].MaxPrice-self.stock_pool[stock].MinPrice))/self.stock_pool[stock].MaxPrice))

            if self.stock_pool[stock].TrendRevered and self.stock_pool[stock].ReversedStockPeriod!=0:
                if high_price > self.stock_pool[stock].ReversedHight:
                   self.stock_pool[stock].ReversedHight = high_price
                   self.stock_pool[stock].ReversedStockPeriod = 8
                   self.stock_pool[stock].DateRevserdHight = np.uint64(convert_date_to_int(context.now))
                self.stock_pool[stock].ReversedStockPeriod -= 1
            if self.stock_pool[stock].TrendRevered and self.stock_pool[stock].ReversedStockPeriod == 0:
                self.stock_pool[stock].decresed_ratio = ((self.stock_pool[stock].MaxPrice - self.stock_pool[stock].MinPrice)) / self.stock_pool[stock].MaxPrice
                self.stock_pool[stock].ReversedRatio = ((self.stock_pool[stock].ReversedHight-self.stock_pool[stock].MinPrice))/self.stock_pool[stock].MinPrice

                logger.info(stock + " trend reversed"+ " DateTimeMax: "+str(self.stock_pool[stock].DateTimeMax)+ " DateTimeMin: "+str(self.stock_pool[stock].DateTimeMin)+" MaxPrice:"+str(self.stock_pool[stock].MaxPrice)+" MinPrice:"+str(self.stock_pool[stock].MinPrice)+" decresed: "+str(((self.stock_pool[stock].MaxPrice-self.stock_pool[stock].MinPrice))/self.stock_pool[stock].MaxPrice))
                self.stock_pool[stock].DecreasedRatio = ((self.stock_pool[stock].MaxPrice - self.stock_pool[stock].MinPrice)) / self.stock_pool[stock].MaxPrice
                logger.info(stock + " trend reversed"+" DateTimeMin: "+str(self.stock_pool[stock].DateTimeMin)+" MinPrice:"+str(self.stock_pool[stock].MinPrice)+" ReversedHight:"+str(self.stock_pool[stock].ReversedHight)+" reversed: "+str(((self.stock_pool[stock].ReversedHight-self.stock_pool[stock].MinPrice))/self.stock_pool[stock].MinPrice))
                self.stock_pool[stock].ReversedRatio = ((self.stock_pool[stock].ReversedHight-self.stock_pool[stock].MinPrice))/self.stock_pool[stock].MinPrice
                #context.sample[context.sample_id] = self.stock_pool[stock]

                sampledata={'BottomDays':self.stock_pool[stock].BottomDays,
                'VolumeBoosted':self.stock_pool[stock].VolumeBoosted,
                'GoldenPrice':self.stock_pool[stock].GoldenPrice,
                'BoostRate':self.stock_pool[stock].BoostRate,
                'MinPrice':self.stock_pool[stock].MinPrice,
                'TrendRevered':self.stock_pool[stock].TrendRevered,
                'DateTimeMax':[int(self.stock_pool[stock].DateTimeMax/1000000)],
                'DateTimeMin':[int(self.stock_pool[stock].DateTimeMin/1000000)],
                'MaxPrice':self.stock_pool[stock].MaxPrice,
                'ReversedHight':self.stock_pool[stock].ReversedHight,
                'DateRevserdHight':[int(self.stock_pool[stock].DateRevserdHight/1000000)],
                'ReversedStockPeriod':self.stock_pool[stock].ReversedStockPeriod,
                'DecreasedRatio': self.stock_pool[stock].DecreasedRatio,
                'ReversedRatio': self.stock_pool[stock].ReversedRatio}
                context.sample=context.sample.append(pd.DataFrame(sampledata))
                del self.stock_pool[stock]

    def display(self):
        for (stock, updated_data) in self.stock_pool.items():
            logger.info(stock+updated_data.tostr())

# 在这个方法中编写任何的初始化逻辑。context对象将会在你的算法策略的任何方法之间做传递。
def init(context):
    logger.info("init")
    all_instrument = all_instruments('CS')
    stocklist = all_instrument.values.tolist()
    context.stocks = []
    context.self_selected_pool = SelfSelectedPool()
    for stock in stocklist:
        #logger.info(stock[13] + ' '+stock[7]+'\n')
        context.stocks.append(stock[7])
    #logger.info(context.stocks)
    #context.stocks = ["000554.XSHE"]

    context.DECLINE_TIME_PERIOD = 34
    context.GOLDEN_RATIO = 0.54
    context.BOTTOM_SHOCK_RATE = 0.22
    context.VOLUME_BoostRate = 2
    context.UNCERTAINTY_RATE = 0.02
    context.DETECT_DAYS = 3
    context.ORDER_PERCENT = 0.2
    context.STOCK_QUANTITY = 8
    context.sample = pd.DataFrame(columns=('BottomDays',
                                            'VolumeBoosted',
                                            'GoldenPrice',
                                            'BoostRate',
                                            'MinPrice',
                                            'TrendRevered',
                                            'DateTimeMax',
                                            'DateTimeMin',
                                            'MaxPrice',
                                            'ReversedHight',
                                            'DateRevserdHight',
                                            'ReversedStockPeriod',
                                            'DecreasedRatio',
                                            'ReversedRatio'))
#result = df1.append(df2)
def before_trading(context):
    pass

def stock_price_equal(stock_price, target, uncertainty_rate):
    return all([(stock_price<(target*(1+uncertainty_rate))),(stock_price>(target*(1-uncertainty_rate)))])


# 你选择的证券的数据更新将会触发此段逻辑，例如日或分钟历史数据切片或者是实时数据切片更新
def handle_bar(context, bar_dict):
    # d = {1:'a',2:'b',3:'c'}
    # s_d =  sorted(d.items(), key=lambda d: d[0], reverse=True)
    cur_positions = context.portfolio.positions
    for stock in cur_positions.keys():
        pnl = cur_positions[stock].pnl
        market_value = cur_positions[stock].market_value
        if pnl/(pnl-market_value)>=0.05 and cur_positions[stock].buytimes<8 and context.portfolio.cash>=10000:
            order_value(stock, 10000)
            logger.info(stock + " fall 5%, buytimes = "+str(cur_positions[stock].buytimes))

        if pnl/(market_value-pnl) >= 0.2:
            order_target_value(stock, 0)
            logger.info(stock + " earn profit 20% and sell out shares")

    count2buy = context.STOCK_QUANTITY - len(cur_positions.keys())

    # TODO: 开始编写你的算法吧！
    context.self_selected_pool.update(context)
    #context.self_selected_pool.display()
    tempdic = {}
    for stock, stockstatus in context.self_selected_pool.stock_pool.items():
        if is_st_stock(stock) == True or stock in cur_positions.keys():
            continue
        if stockstatus.VolumeBoosted == True and stockstatus.TrendRevered == True:
            tempdic[stockstatus.BoostRate] = stock
    if count2buy>0 and len(tempdic)>0:
        if len(tempdic)>count2buy:
            descenddic = sorted(tempdic.items(),key=lambda d:d[0],reverse=True)
            for BoostRate,stock in descenddic[0:count2buy]:
                #target_available_cash = context.portfolio.cash * context.ORDER_PERCENT
                if context.portfolio.cash>=10000:
                    order_value(stock, 10000)
                    logger.info(stock + " bottom boosted 2 times and buy 10000 market value for 1st times")
                    deb = 1
                #buy_qty = context.portfolio.positions[stock].buy_quantity

        else:
            for BoostRate, stock in tempdic.items():
                if context.portfolio.cash>=10000:
                    order_value(stock, 10000)
                    logger.info(stock + " bottom boosted 2 times and buy 10000 market value for 1st times")
                    deb = 1
                #stock_position = context.portfolio.positions[stock]
    DEBUG = 1