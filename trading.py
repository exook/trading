from pandas_datareader import data
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
import sys
import pickle

#python3 trading.py may22 26500 ana

def get_prices(path,list_of_strategies):
    ticker_list=[]
    for strategy in list_of_strategies:
        ticker_list.extend(strategy["Ticker"])
    
    ticker_list = list(set(ticker_list))
    
    today = date.today()
    
    price_dict = {}
    
    for ticker in ticker_list:
        price = data.DataReader((ticker+".ST").replace(" ","-"), 'yahoo', today, today)["Close"].iloc[0]
        print(ticker+":\t"+str(round(price,2)))
        price_dict[ticker]=price
            
    with open(path+"price_dict.pickle", 'wb') as f:
        pickle.dump(price_dict, f)

def ana(path,list_of_strategies,money_per_strategy,money_per_stock):
    price_dict = pd.read_pickle(path+"price_dict.pickle")
    
    for strategy in list_of_strategies:
        strategy["Price"] = strategy.apply(lambda row : price_dict[row["Ticker"]],axis=1)
    
    optimal_holdings_dict = {"Ticker":[], "Price":[], "Amount_to_buy":[],"Total_Price":[]}
    for strategy in list_of_strategies:
        strategy=strategy[["Ticker","Price"]]
        strategy["Amount_to_buy"] = strategy.apply(lambda row, money_per_stock=money_per_stock: int(money_per_stock//row["Price"]), axis=1)
        strategy["Total_Price"] = strategy.apply(lambda row: row["Amount_to_buy"]*row["Price"], axis=1)
        strategy.loc[0,"Liquid_Assets"] = money_per_strategy-strategy.loc[0,"Total_Price"]
        
        strategy.loc[0,"Liquid_Assets"] = money_per_strategy-strategy.loc[0,"Total_Price"]
        for i in range(1,len(strategy)):
            strategy.loc[i,"Liquid_Assets"] = strategy.loc[i-1,"Liquid_Assets"]-strategy.loc[i,"Price"]*strategy.loc[i,"Amount_to_buy"]
        strategy = strategy[strategy.Liquid_Assets > 0]
        strategy = strategy[strategy.Amount_to_buy > 0]
        strategy = strategy[["Ticker","Price","Total_Price","Amount_to_buy"]]
        #print(strategy)
        optimal_holdings_dict["Ticker"].extend(strategy["Ticker"])
        optimal_holdings_dict["Amount_to_buy"].extend(strategy["Amount_to_buy"])
        optimal_holdings_dict["Price"].extend(strategy["Price"])
        optimal_holdings_dict["Total_Price"].extend(strategy["Total_Price"])
        optimal_holdings_df = pd.DataFrame(data=optimal_holdings_dict)
        
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
    
    buy_df.to_csv(path+"buy.csv", sep=',', encoding='utf-8',index=False)    
    
def main():
    input_amount = int(sys.argv[2])

    number_of_strategies = 4
    number_of_stocks_per_strategy = 10

    money_per_strategy = input_amount/number_of_strategies
    money_per_stock = money_per_strategy/number_of_stocks_per_strategy

    pd.options.mode.chained_assignment = None  # default='warn'

    path = sys.argv[1]+"/"

    list_of_strategies = [
        pd.read_csv(path+"Svenska aktier - Borslabbet.csv", index_col=None, header=0),
        pd.read_csv(path+"Svenska aktier - Borslabbet(1).csv", index_col=None, header=0),
        pd.read_csv(path+"Svenska aktier - Borslabbet(2).csv", index_col=None, header=0),
        pd.read_csv(path+"Svenska aktier - Borslabbet(3).csv", index_col=None, header=0),
    ]

    if sys.argv[3]=="price":
        get_prices(path,list_of_strategies)
    elif sys.argv[3]=="ana":
        ana(path,list_of_strategies,money_per_strategy,money_per_stock)
    else:
        print("No such command")

if __name__ == '__main__':
    main()

