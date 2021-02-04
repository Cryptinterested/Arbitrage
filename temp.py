# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
from typing import Tuple, List
from math import log
from binance.client import Client
import time
import pyexcel


API_KEY = "***"
SECRET_KEY = "***"

#CONNECTION TO BINANCE API
def connectToBinanceAPI(API_KEY, SECRET_KEY) :
    client = Client(API_KEY, SECRET_KEY)
    return client

#DICO OF ALL PAIRS + PRICES
def getAllTickers(client) :
    prices = client.get_all_tickers()
    return prices

#TRANSFORM TO DICO -> "PAIR" : PRICE
def transformTickersToDicoPairPrice(prices) :
    prices_aux ={pair['symbol'] : float(pair['price']) for pair in prices}
    return prices_aux

#TO GET ALL CURRENCIES LISTED ON USDT
def getSingleCurrencies(prices) :
    PAIRS_USDT = [elt['symbol'] for elt in prices if elt['symbol'][-4:] == 'USDT' and 'UP' not in elt['symbol'] and 'DOWN' not in elt['symbol'] and 'BULL' not in elt['symbol']]
    SINGLE_CURRENCY = [curr[:-4] for curr in PAIRS_USDT]
    return SINGLE_CURRENCY

def currExists(currency_price,client):
    #print(client.get_symbol_info(currency_price))
    return client.get_symbol_info(currency_price)

#BUILD ADJACENCY MATRIX OF ALL PAIRS
def AdjacencyMatrixPairs(SINGLE_CURRENCY,client) :
    print("Matrix is building ...")
    ADJACENCY_MATRIX = []
    for i in range(len(SINGLE_CURRENCY)) :
        AUX = []
        for j in range(len(SINGLE_CURRENCY)) :
            if i == j or currExists(SINGLE_CURRENCY[i]+SINGLE_CURRENCY[j], client) == None :
                AUX.append(1)
            else :
                AUX.append(SINGLE_CURRENCY[i]+SINGLE_CURRENCY[j])
        ADJACENCY_MATRIX.append(AUX)
    return ADJACENCY_MATRIX

#BUILD ADJACENCY MATRIX OF ALL PRICES
def AdjacencyMatrixPrices(ADJACENCY_MATRIX, prices_aux) :
    ADJACENCY_MATRIX_PRICES = ADJACENCY_MATRIX.copy()
    for i in range(len(ADJACENCY_MATRIX)) :
        for j in range(len(ADJACENCY_MATRIX[i])) :
            #BROWSE THE PRICES
            if i != j :
                currency_price = prices_aux.get(ADJACENCY_MATRIX[i][j])
                if currency_price != None :
                    ADJACENCY_MATRIX_PRICES[i][j] = currency_price
                else :
                     ADJACENCY_MATRIX_PRICES[i][j] = 1
    return ADJACENCY_MATRIX_PRICES
                

def buyTest(client, pair_name, amount) :
    order = client.create_test_order(
            symbol=pair_name,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=float(amount))
    return order


def sellTest(client, pair_name, amount) :
    order = client.create_test_order(
            symbol=pair_name,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=float(amount))
    return order


def negate_logarithm_convertor(graph: Tuple[Tuple[float]]) -> List[List[float]]:
    ''' log of each rate in graph and negate it'''
    result = [[-log(edge) for edge in row] for row in graph]
    return result


def arbitrage(currency_tuple: tuple, rates_matrix: Tuple[Tuple[float, ...]]):
    ''' Calculates arbitrage situations and prints out the details of this calculations'''

    trans_graph = negate_logarithm_convertor(rates_matrix)

    # Pick any source vertex -- we can run Bellman-Ford from any vertex and get the right result

    source = 0
    n = len(trans_graph)
    min_dist = [float('inf')] * n

    pre = [-1] * n
    
    min_dist[source] = source

    # 'Relax edges |V-1| times'
    for _ in range(n-1):
        for source_curr in range(n):
            for dest_curr in range(n):
                if min_dist[dest_curr] > min_dist[source_curr] + trans_graph[source_curr][dest_curr]:
                    min_dist[dest_curr] = min_dist[source_curr] + trans_graph[source_curr][dest_curr]
                    pre[dest_curr] = source_curr

    # if we can still relax edges, then we have a negative cycle
    ALL_ARBITRAGE_PAIRS =[]
    CURRENCIES_TO_BUY = []
    for source_curr in range(n):
        for dest_curr in range(n):
            if min_dist[dest_curr] > min_dist[source_curr] + trans_graph[source_curr][dest_curr]:
                # negative cycle exists, and use the predecessor chain to print the cycle
                print_cycle = [dest_curr, source_curr]
                # Start from the source and go backwards until you see the source vertex again or any vertex that already exists in print_cycle array
                while pre[source_curr] not in  print_cycle:
                    print_cycle.append(pre[source_curr])
                    source_curr = pre[source_curr]
                print_cycle.append(pre[source_curr])
                                
                #FEES CALCULATION TAKER SIDE
                singl_curr = [currencies[p] for p in print_cycle[::-1]]
                #print("Arbitrage Opportunity: ", , "\n")
                #print(" --> ".join([currencies[p] for p in print_cycle[::-1]]))
                
                PAIRS = [0]*len(singl_curr)
                for i,elt in enumerate(singl_curr) :
                    if i == 0 :
                        PAIRS[i] = singl_curr[0]+'USDT'
                    else :
                        PAIRS[i] = singl_curr[i]+singl_curr[i-1]
                PAIRS.append(singl_curr[len(singl_curr)-1]+'USDT')
                ALL_ARBITRAGE_PAIRS.append(PAIRS)
                CURRENCIES_TO_BUY.append(singl_curr)
    return ALL_ARBITRAGE_PAIRS, CURRENCIES_TO_BUY             
  

def isProfitable(SINGLE_CURRENCY, initial_amount, client):
    return initial_amount - (0.001*float(client.get_asset_balance(asset=SINGLE_CURRENCY)['free'])) < initial_amount

def performArbitrage(all_arbitrage_pairs, currencies_to_buy, initial_amount, client):
    amount = initial_amount
    tab_to_avoid = []
    for index, tab_pair in enumerate(all_arbitrage_pairs) :
        #THE OPERATIONS
        for i in range(len(tab_pair)-1) :
            print(tab_pair[i])
            res = buyTest(client, tab_pair[i] , amount)
            if res == False :
                tab_to_avoid.append(index)
                break
        res = sellTest(client, tab_pair[len(tab_pair)-1], amount)
        if res == False :
                tab_to_avoid.append(index)
    return tab_to_avoid

if __name__ == "__main__":
    
    #start = time.time()
    
    daniel_client = connectToBinanceAPI(API_KEY, SECRET_KEY)  
    CASH_IN = 30.0
    
    current_pairs_prices = getAllTickers(daniel_client)  
    dico_pairs_prices = transformTickersToDicoPairPrice(current_pairs_prices)  
    currencies = getSingleCurrencies(current_pairs_prices)  
    adjacency_pairs_matrix = AdjacencyMatrixPairs(currencies,daniel_client)
    print("End matrix building.")
    ''' Visual of the matrix '''
    pyexcel.save_as(array=adjacency_pairs_matrix, dest_file_name="/home/danub0/Documents/Arbitrage Bot/pairs.xls")
    print("Let's start !")
    while True :
        current_pairs_prices = getAllTickers(daniel_client)  
        dico_pairs_prices = transformTickersToDicoPairPrice(current_pairs_prices)  
        currencies = getSingleCurrencies(current_pairs_prices)  
        rates = AdjacencyMatrixPrices(adjacency_pairs_matrix, dico_pairs_prices)
        #print(rates)
        ''' Visual of the pair matrix'''
        pyexcel.save_as(array=rates, dest_file_name="/home/danub0/Documents/Arbitrage Bot/prices.xls")

        all_arbitrage_pairs, currencies_to_buy = arbitrage(currencies, rates) #LIST OF PAIRS TO BUY AND LIST OF CURRENCIES ONLY
        #print(all_arbitrage_pairs)
        print(currencies_to_buy)
        
        print(performArbitrage(all_arbitrage_pairs, currencies_to_buy, CASH_IN, daniel_client))
        
        time.sleep(6)
        
    #end = time.time()
    #print("\nTotal Execution time : {} sec".format(end-start))
    
    #IDEE : TOUT COTER SUR DU BUSD


# Time Complexity: O(N^3)
# Space Complexity: O(N^2)

# 1) next step : hard code dico of fees
# 2) get prices and construct matrice on a minute basis
# 3) adjust fees to be accurate