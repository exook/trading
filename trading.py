import pandas_datareader
from pandas_datareader import data
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
import sys
import pickle
import requests
import apikey_module as apikey_module

def get_exchange_dict(list_of_market_places,currency_dict):
    exchange_dict={}
    apikey = apikey_module.apikey

    for market in list_of_market_places:
        current_currency = currency_dict[market]
        if current_currency == "SEK":
            exchange_dict[market]=1
        else:
            print(current_currency)
            url = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={current_currency}&to_currency=SEK&apikey={apikey}'
            r = requests.get(url)
            data = r.json()
            rate=float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
            exchange_dict[market]=rate
    return exchange_dict


#python3 trading.py may22 26500 ana usa

def get_prices(path,list_of_strategies,list_of_market_places,market_abbr):
    ticker_list=[]
    
    for strategy in list_of_strategies:
        ticker_list.extend(strategy["Ticker"])
    
    ticker_list = list(set(ticker_list))

    print(f"Ticker list length: {len(ticker_list)}\n")
    
    #FIXME
    today = date.today()
    #today="2022-09-29"
    price_dict={}

    currency_dict = {".ST":"SEK","":"USD",".OL":"NOK",".CO":"DKK",".HE":"EUR"}
    exchange_dict = get_exchange_dict(list_of_market_places,currency_dict)
    
    for ticker in ticker_list:
        skip = 0
        price_list_from_different_markets = []
        print("")
        for market in list_of_market_places:
            try:
                price = data.DataReader((ticker+market).replace(" ","-"), 'yahoo', today, today)["Close"].iloc[0] * exchange_dict[market]
                print(ticker+market+":\t"+str(round(price,2)))
                price_list_from_different_markets.append(price)

                if market_abbr == "nord" and market == ".ST":
                    skip = 1
                    print("^skipping ^")
                    continue

                price_dict[ticker]=price
            except pandas_datareader._utils.RemoteDataError:
                print(ticker+market+" Not found")
                continue
            except KeyError: # If you get a keyerror at the right market it does not make an entry
                print(ticker+market+" KeyError")
                input(f"Input temporary price for '{ticker}' in {currency_dict[market]}: ")

        if len(price_list_from_different_markets)>1:
            print("Stock found in multiple markets, manually input price for '{ticker}' in {currency_dict[market]}")
            actual_price = float(input("Input: "))*exchange_dict[market]
        elif len(price_list_from_different_markets)==0:
            print(f"Stock not found in any market, manually input price for '{ticker}' in {currency_dict[market]}")
            actual_price = float(input("Input: "))*exchange_dict[market]
        elif len(price_list_from_different_markets)==1:
            actual_price = price_list_from_different_markets[0]
        else:
            print("UNKNOWN ERROR")
            sys.exit()

        if skip:
            continue
        elif actual_price < 0:
            continue
        else:
            price_dict[ticker]=actual_price
            
    with open(path+f"price_dict_{market_abbr}.pickle", 'wb') as f:
        pickle.dump(price_dict, f)
    #price_df = pd.DataFrame(price_dict)
    #price_df.to_csv(path+f"price_dict_{market_abbr}.csv", sep=',', encoding='utf-8',index=False)

def ana(path,list_of_strategies,money_per_strategy,money_per_stock,market_abbr):
    price_dict = pd.read_pickle(path+f"price_dict_{market_abbr}.pickle")
    list_of_tickers_in_price_dict = list(price_dict.keys())

    # Really weird fix
    for i in range(0,len(list_of_strategies)):
        strategy_temp = list_of_strategies[i][list_of_strategies[i]['Ticker'].isin(list_of_tickers_in_price_dict)]
        strategy_temp.reset_index(inplace=True)
        list_of_strategies[i] = strategy_temp

    # Add the prices form the price dict as a new column to the strategy
    for strategy in list_of_strategies:
        strategy["Price"] = strategy.apply(lambda row : price_dict[row["Ticker"]],axis=1)

    # Create a dictionary to hold the optimal holdings
    optimal_holdings_dict = {"Ticker":[], "Price":[], "Amount_to_buy":[],"Total_Price":[]}
    for strategy in list_of_strategies:
        # Slim down columns
        strategy=strategy[["Ticker","Price"]]
        # Calculate how many stocks per stock to buy
        strategy["Amount_to_buy"] = strategy.apply(lambda row, money_per_stock=money_per_stock: int(money_per_stock//row["Price"]), axis=1)
        strategy["Total_Price"] = strategy.apply(lambda row: row["Amount_to_buy"]*row["Price"], axis=1)
        strategy.loc[0,"Liquid_Assets"] = money_per_strategy-strategy.loc[0,"Total_Price"]
        
        for index, row in strategy.iterrows():
            if index == 0:
                continue
            print(index)
            strategy.loc[index,"Liquid_Assets"] = strategy.loc[index-1,"Liquid_Assets"]-strategy.loc[index,"Price"]*strategy.loc[index,"Amount_to_buy"]
        strategy = strategy[strategy.Liquid_Assets > 0]
        strategy = strategy[strategy.Amount_to_buy > 0]
        strategy = strategy[["Ticker","Price","Total_Price","Amount_to_buy"]]
        #print(strategy)
        optimal_holdings_dict["Ticker"].extend(strategy["Ticker"])
        optimal_holdings_dict["Amount_to_buy"].extend(strategy["Amount_to_buy"])
        optimal_holdings_dict["Price"].extend(strategy["Price"])
        optimal_holdings_dict["Total_Price"].extend(strategy["Total_Price"])
        optimal_holdings_df = pd.DataFrame(data=optimal_holdings_dict)
    
    #sum if
    optimal_holdings_df['Merged_Amount'] = optimal_holdings_df.groupby(['Ticker'])['Amount_to_buy'].transform('sum')
    optimal_holdings_df['Merged_Price'] = optimal_holdings_df.apply(lambda row:row["Merged_Amount"]*row["Price"], axis=1)
    optimal_holdings_df = optimal_holdings_df.drop_duplicates(subset=['Ticker'])
    optimal_holdings_df = optimal_holdings_df[["Ticker","Merged_Amount"]]
    optimal_holdings_df.to_csv(path+"optimal.csv", sep=',', encoding='utf-8',index=False)
        
    current_holdings_df = pd.read_csv(path+"current_holdings.csv", index_col=None, header=0)
    
    current_holdings_df["Merged_Amount"]=current_holdings_df["Amount"]*(-1)
    buy_df = optimal_holdings_df.append(current_holdings_df)[["Ticker","Merged_Amount"]]

    buy_df['New_Merged_Amount'] = buy_df.groupby(['Ticker'])['Merged_Amount'].transform('sum')
    buy_df = buy_df.drop_duplicates(subset=['Ticker'])
    buy_df = buy_df[["Ticker","New_Merged_Amount"]]
    buy_df = buy_df.sort_values(by="New_Merged_Amount", ascending=True)
    print(buy_df)
    
    buy_df.to_csv(path+f"buy_{market_abbr}.csv", sep=',', encoding='utf-8',index=False)    
    
def main():
    input_amount = int(sys.argv[2])

    market_dict=    {
                    "se":["Svenska aktier",[".ST"]],
                    "nord":["Nordiska aktier",[".OL",".CO",".HE",".ST"]],
                    "usa":["Amerikanska aktier",[""]],
                    }

    market_raw_data = market_dict[sys.argv[4]][0]
    list_of_market_places=market_dict[sys.argv[4]][1]
    market_abbr = sys.argv[4]

    if market_abbr == "se" or market_abbr == "nord":
        number_of_strategies = 4
    if market_abbr == "usa":
        number_of_strategies = 3

    
    number_of_stocks_per_strategy = 10

    money_per_strategy = input_amount/number_of_strategies
    money_per_stock = money_per_strategy/number_of_stocks_per_strategy

    pd.options.mode.chained_assignment = None  # default='warn'

    path = sys.argv[1]+"/"+market_abbr+"/"

    list_of_strategies = []

    list_of_strategies.append(pd.read_csv(path+f"{market_raw_data} - Borslabbet.csv", index_col=None, header=0,nrows=20))
    for i in range(1,number_of_strategies):
        list_of_strategies.append(pd.read_csv(path+f"{market_raw_data} - Borslabbet({i}).csv", index_col=None, header=0,nrows=20))

    if sys.argv[3]=="price":
        get_prices(path,list_of_strategies,list_of_market_places,market_abbr)
    elif sys.argv[3]=="ana":
        ana(path,list_of_strategies,money_per_strategy,money_per_stock,market_abbr)
    else:
        print("No such command")

if __name__ == '__main__':
    main()

