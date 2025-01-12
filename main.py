"""
Created on Sunday Jan 05 20:23:00 2025
This scripts contains the main.py file. Execute this file to get the results
"""

# Standard library imports
import warnings
warnings.filterwarnings('ignore')

# personal imports
from utils.getdata import GetData
from utils.updateindex import UpdateIndex

if __name__ == '__main__':
    
    year='2024'
    trader= 'Pelosi' # can be set to trader='all' to get all the traders

    # Get the data
    gd = GetData(trader, year)
    gd.fetch_trades()
    gd.extract_trades_from_pdf() #Nancy_Pelosi_2_23_2024.pdf
