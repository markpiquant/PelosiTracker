"""
Created on Sunday Jan 13 00:23:00 2025
This scripts contains the UpdateIndex class used to create the index from the JSON containing congress trades
"""
# Standard library imports

import yfinance as yf
from yahooquery import search
from fuzzywuzzy import fuzz
import json

# personal imports
from utils.Paths import PATH, DATAPATH

class UpdateIndex():
    def __init__(self):
        self.index = None
        self.companies = None
        self.trades = None
        self.positions = None
        self.index

    @staticmethod
    def update_positions():
        """
        will open each json of a trader transaction file. and will create a JSON that sums up all 
        the position of a trader up to the most recent date
        
        """
        for trader_folder in DATAPATH.iterdir(): # Parcourir chaque sous-dossier dans DATAPATH
            if trader_folder.is_dir(): # Si le sous-dossier est un dossier
                positions = {}
                for json_file in trader_folder.glob("*.json"):
                    if json_file.name ==  "current_position.json":
                        continue
                    with open(json_file, 'r') as file:
                        data = json.load(file)
                        for transaction in data.values():
                            isin = transaction["ISIN"]
                            amount_range = transaction["Amount"].replace("$", "").replace(",", "").split(" - ")
                            if len(amount_range) == 1:
                                avg_amount = float(amount_range[0])
                            else:
                                avg_amount = (float(amount_range[0]) + float(amount_range[1])) / 2
                            date = transaction["Date"]
                            
                            if isin not in positions:
                                positions[isin] = {
                                    "Company": transaction["Company"],
                                    "aggregated_value": 0,
                                    "transactions": []
                                }
                            
                            if transaction["Action"] in ["P", "S", "s"]:
                                if transaction["Action"] == "P":
                                    positions[isin]["aggregated_value"] += avg_amount
                                else: # "S" or "s"
                                    positions[isin]["aggregated_value"] -= avg_amount
                                
                                positions[isin]["transactions"].append({
                                    "date": date,
                                    "amount": avg_amount,
                                    "description": transaction["Description"]["original"],
                                    "action": transaction["Action"],
                                    "Av_Stock_price_at_t0": transaction["Av_Stock_price_at_t0"]
                                })
                
                # Save the positions to a new JSON file
                output_file = trader_folder / "current_position.json"
                with open(output_file, 'w') as outfile:
                    json.dump(positions, outfile, indent=4)
                
        