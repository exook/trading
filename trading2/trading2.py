import pandas_datareader
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
import sys
import pickle

#Start the download with:   time python3 trading2.py download
#Plot the data with:        python3 trading2.py plot

# Downloading all Swedish stocks took 36 min

def download():
    #Get the tickers from file into dataframe
    ticker_df = pd.read_csv("svenska_bolag.csv", index_col=None, header=0)

    #Prepare dictionary to hold historical prices for the different tickers
    price_dict = {}
    #Prepare list to hold tickers that failed
    exception_list = []

    #Loop over all the tickers 
    for ticker in ticker_df.Ticker:
        print(ticker)
        
        #Try to get data for the ticker
        try:
            historical_prices = pandas_datareader.data.DataReader((str(ticker)+".ST").replace(" ","-"), 'yahoo', "1900-01-01", date.today())
            price_dict[ticker]=historical_prices
            print("\n")
        #Create exceptions for when the ticker is not avaliable on YAHOO Finance
        except pandas_datareader._utils.RemoteDataError:
            print("Ticker not found\n")
            exception_list.append(ticker)
        except KeyError:
            print("Maybe private\n")
            exception_list.append(ticker)
            
    #Save the price dictionary
    with open("price_dict.pickle", 'wb') as f:
        pickle.dump(price_dict, f)
    #Save the exception list
    with open("exception_list.pickle", 'wb') as f:
        pickle.dump(exception_list, f)
        
def plot():
    
    #Read the price dictionary and exception list
    price_dict = pd.read_pickle("price_dict.pickle")
    exception_list = pd.read_pickle("exception_list.pickle")
    
    #Print some stats
    print(f"Number of accessible stocks: {len(price_dict.items())}")
    print(f"Number of skipped stocks: {len(exception_list)}")

    #Initialize figure
    fig, ax = plt.subplots()

    #Loop over tickers
    for ticker in price_dict:
        #Plot Close price vs date for each ticker
        ax.plot(price_dict[ticker].index,price_dict[ticker]["Close"])
    
    #Set y-axis limits
    ax.set_ylim(0,2000)
    #Set labels and title
    ax.set(xlabel='Time', ylabel='Price (kr)', title=f'Stock Price vs Time of {len(price_dict.items())} Swedish Companies')
    #Add grid
    ax.grid()
    #Save figure
    fig.savefig("all_stocks.png")

def test():
    ticker = "ABB"
    today = date.today()
    start_date = "1900-01-01"
    end_date = date.today()
    history = pandas_datareader.data.DataReader((str(ticker)+".ST").replace(" ","-"), 'yahoo', start_date, today)
    print(history.head())
    

def main():
    if sys.argv[1]=="download":
        download()
    elif sys.argv[1]=="plot":
        plot()
    elif sys.argv[1]=="test":
        test()
    else:
        print("No such command")

if __name__ == "__main__":
    main()
