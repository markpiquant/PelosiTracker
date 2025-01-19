"""
Created on Sunday Jan 13 00:23:00 2025
This scripts contains the UpdateIndex class used to create the index from the JSON containing congress trades
"""
# Standard library imports
from datetime import datetime
import re
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
                    if json_file.name == "current_position.json":
                        continue
                    with open(json_file, 'r') as file:
                        data = json.load(file)
                        for transaction in data.values():
                            # print(transaction)
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
                                    "transactions": {
                                        "stocks": [],
                                        "options": [],
                                        "autres": []
                                    }
                                }
                            
                            if transaction["Description"]["type"] == "Stock":
                                if transaction["Action"] == "P":
                                    positions[isin]["aggregated_value"] += avg_amount
                                else: # "S" or "s"
                                    positions[isin]["aggregated_value"] -= avg_amount
                            
                            # Estimation de la position réelle
                            shares_pattern = re.search(r'(Purchased|Sold) (\d+,\d+|\d+) shares', transaction["Description"]["original"])
                            if shares_pattern:
                                shares = int(shares_pattern.group(2).replace(",", ""))
                                estimated_real_position_size = shares * transaction["Av_Stock_price_at_t0"]
                            else:
                                estimated_real_position_size = 0

                            transaction_entry = {
                                "date": date,
                                "amount": avg_amount,
                                "description": transaction["Description"]["original"],
                                "action": transaction["Action"],
                                "Av_Stock_price_at_t0": transaction["Av_Stock_price_at_t0"],
                                "estimated_real_position_size": estimated_real_position_size
                            }
                            
                            if transaction["Description"]["type"] == "Stock":
                                positions[isin]["transactions"]["stocks"].append(transaction_entry)
                            elif transaction["Description"]["type"] == "Call Option" or transaction["Description"]["type"] == "Put Option":
                                positions[isin]["transactions"]["options"].append(transaction_entry)
                            else:
                                positions[isin]["transactions"]["autres"].append(transaction_entry)

                # Trier les transactions par date du plus récent au moins récent
                for isin in positions:
                    for key in ["stocks", "options", "autres"]:
                        positions[isin]["transactions"][key].sort(key=lambda x: datetime.strptime(x["date"], "%m/%d/%Y"), reverse=True)
                
                # Save the positions to a new JSON file
                output_file = trader_folder / "current_position.json"
                with open(output_file, 'w') as outfile:
                    json.dump(positions, outfile, indent=4)
                    
        