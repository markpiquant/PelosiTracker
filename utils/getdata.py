"""
Created on Sunday Jan 05 20:23:00 2025
This scripts contains the GetData class used to retrieve trades
"""
# Standard library imports
import csv, zipfile
import requests
import os
import fitz # PyMuPDF
import json
import re
import itertools
import yfinance as yf
from datetime import timedelta
from datetime import datetime
from yahooquery import search
from fuzzywuzzy import fuzz

# personal imports
from utils.Paths import PATH, DATAPATH
from utils.API_KEYS import FMP_KEY

class GetData:
    def __init__(self, trader, year):
        self.trader = trader
        self.year = year
        self.ticker_database_path = DATAPATH / 'ticker_database.json'
        self.load_ticker_database() 

    def load_ticker_database(self):
        try:
            with open(self.ticker_database_path, 'r') as file:
                self.ticker_database = json.load(file)
        except FileNotFoundError:
            self.ticker_database = {}

    def save_ticker_database(self):
        with open(self.ticker_database_path, 'w') as file:
            json.dump(self.ticker_database, file, indent=4)

    def download_and_extract_zip(self, zip_file_url, zipfile_name):
        """
        Downloads and extracts a ZIP file from the given URL.

        Args:
            zip_file_url (str): URL to download the ZIP file.
            zipfile_name (str): Name of the downloaded ZIP file.
        """
        r = requests.get(zip_file_url)
        with open(zipfile_name, 'wb') as f:
            f.write(r.content)

        with zipfile.ZipFile(zipfile_name) as z:
            z.extractall('.')

    def read_csv_and_process_trades(self, year, pdf_file_url):
        """
        Reads the CSV file and processes the trades for the specified year.

        Args:
            year (int): Year of the financial disclosures.
            pdf_file_url (str): Base URL to download individual PDF files.
        """
        with open(f'{year}FD.txt') as f:
            i = 0
            reader = csv.reader(f, delimiter='\t')
            next(reader)  # Skip the header
            for line in reader:
                if self.trader == 'all' or line[1] == self.trader:
                    trader_name, doc_id = line[1], line[8]
                    name = f"{line[2]}_{line[1]}_{line[7].replace('/', '_')}"
                    r = requests.get(f"{pdf_file_url}{doc_id}.pdf")

                    trader_path = DATAPATH / trader_name
                    os.makedirs(trader_path, exist_ok=True)

                    pdf_path = os.path.join(trader_path, f"{name}.pdf")
                    with open(pdf_path, 'wb') as pdf_file:
                        pdf_file.write(r.content)
                    i += 1

        # Remove the .zip, .txt, and .xml files
        os.remove(f'{year}.zip')
        os.remove(f'{year}FD.txt')
        xml_filename = f'{year}FD.xml'
        if os.path.exists(xml_filename):
            os.remove(xml_filename)

        print('======= Data fetched successfully =======')
        print(f'======= {i} trade declarations founds for {self.trader} in {year} =======')

    def fetch_trades(self):
        """
        Fetches trade data for the specified trader and year.

        This function downloads a ZIP file containing financial disclosure PDFs,
        extracts the contents, and processes the relevant files for the specified
        trader. If 'all' traders are specified, it processes files for all traders.
        The function saves the PDFs to the appropriate directories and renames them
        based on the trader's name and the document ID. Finally, it removes the
        temporary ZIP, TXT, and XML files.
        """
        if self.year == "all":
            current_year = datetime.now().year
            for year in range(current_year - 5, current_year + 1):
                zip_file_url = f'https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.ZIP'
                pdf_file_url = f'https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/'
                zipfile_name = f'{year}.zip'

                self.download_and_extract_zip(zip_file_url, zipfile_name)
                self.read_csv_and_process_trades(year, pdf_file_url)
        else:
            zip_file_url = f'https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{self.year}FD.ZIP'
            pdf_file_url = f'https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{self.year}/'
            zipfile_name = f'{self.year}.zip'

            self.download_and_extract_zip(zip_file_url, zipfile_name)
            self.read_csv_and_process_trades(self.year, pdf_file_url)

    def extract_trades_from_pdf(self):
        '''
        Pour tous les nouveaux fichiers téléchargés, on extrait les données des transactions et on les enregistre dans un fichier JSON.
        '''
        for trader_folder in DATAPATH.iterdir():# Parcourir chaque sous-dossier dans DATAPATH
            if trader_folder.is_dir():
                for pdf_file in trader_folder.glob("*.pdf"):# Parcourir chaque fichier PDF dans le sous-dossier
                    try:
                        doc = fitz.open(pdf_file)
                        doc.close()
                    except:
                        print(f"Deleting corrupt PDF: {pdf_file}")
                        os.remove(pdf_file)
                        continue
                    json_file = pdf_file.with_suffix('.json')
                    if not json_file.exists(): # Appeler process_pdf si le fichier JSON n'existe pas
                        self.process_pdf(pdf_file)
                        
    def process_pdf(self,pdf_path):
        # Ouvrir le document PDF
        doc = fitz.open(pdf_path)

        # Initialiser une liste pour stocker les données du tableau
        transactions = []

        # Parcourir chaque page du document
        for page in doc:
            # Rechercher le texte "Owner" sur la page
            text_instances = page.search_for("Owner")
            
            # Si le texte "Owner" est trouvé
            if text_instances:
                # Extraire le texte de la page
                page_text = page.get_text("text")
                
                # Diviser le texte en lignes
                lines = page_text.split('\n')
                # Trouver l'index du début du tableau
                try:
                    start_index = next(i for i, line in enumerate(lines) if "Owner" in line)
                except :
                    start_index = next(i for i, line in enumerate(lines) if "owner asset" in line)
                
                # Extraire les lignes suivantes qui contiennent les données du tableau
                for line in lines[start_index + 1:]:
                    if line.strip() == "":
                        break
                    transactions.append(line.strip())
        # On reformate le json en commençant par supprimer tout après l'index contenant "* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.",
        try:
            transactions = transactions[:transactions.index("* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.")]
        except:
            pass
        ABREV_trader=transactions[transactions.index('$200?')+1] # the first element is the name of the trader
        split_transactions=[list(group) for key, group in itertools.groupby(transactions, lambda x: x == ABREV_trader) if not key] 
        d, i = {}, 1 
        for elem in split_transactions[1:]:
            # Vérifier si l'élément contient 'S', 'P', 'S (partial)', ou 'P (partial)' comme mots complets
            if re.search(r'(.*?)(?<![./-])\b(S|P)\b(?![./-])|\bS \(partial\)\b|\bP \(partial\)\b', elem[0]):
                # Diviser l'élément en deux et reformater la liste
                match = re.search(r'(.*?)(?<![./-])\b(S|P)\b(?![./-])|\bS \(partial\)\b|\bP \(partial\)\b', elem[0])
                if match:
                    elem = [match.group(1).strip(), match.group(2)] + elem[1:]
            print(elem)

            while elem[1].lower() not in ['p','s','p (partial)','s (partial)', 'e']:
                elem=[elem[0]]+elem[2:]

            # Cleaning des dates
            if len(elem[2])==21:
                elem[2]=elem[2][:10]
            elif len(elem[2])==10:
                elem=elem[:3]+elem[4:]
            
            # cleaning des amounts
            try:
                if len(elem[3].split('-')[1])==0:
                    elem[3]=elem[3].split('-')[0]+'- '+elem[4]
                    elem=elem[:4]+elem[5:]
            except: # pour les cas on a pas de "-"
                pass 
            # rangement des données dans un dictionnaire
            d['Transaction ' + str(i)] = {}
            d['Transaction ' + str(i)]['Company'] = elem[0]
            ticker=GetData.get_ticker_from_name(self,elem[0])
            d['Transaction ' + str(i)]['Ticker'] = ticker

            if elem[0] in self.ticker_database.keys() and self.ticker_database[elem[0]]['isin']!='NA':
                d['Transaction ' + str(i)]['ISIN'] = self.ticker_database[elem[0]]['isin']
            else:
                d['Transaction ' + str(i)]['ISIN'] = GetData.get_isin_from_ticker(self,elem[0],ticker)

            d['Transaction ' + str(i)]['Action'] = elem[1]
            d['Transaction ' + str(i)]['Date'] = elem[2]
            d['Transaction ' + str(i)]['Amount'] = elem[3]
            d['Transaction ' + str(i)]['Av_Stock_price_at_t0'] = GetData.get_average_stock_price(ticker, datetime.strptime(elem[2], "%m/%d/%Y").strftime("%Y-%m-%d"))
            try:
                description = elem[5].replace("D\u0287\u0295\u0285\u0294\u028b\u0292\u0296\u028b\u0291\u0290: ", "")
            except IndexError:
                description= 'None'
               
            investment_type = GetData.identify_investment_type(description)
            d['Transaction ' + str(i)]['Description']  = {
                    "type": investment_type,
                    "original": description, 
            }

            if d['Transaction ' + str(i)]['Description']['type']=="Option":
                    expiration_date, strike_price= GetData.extract_option_details(d['Transaction ' + str(i)]['Description']['original'])
                    GetData.get_call_option_price(ticker,expiration_date, strike_price)
                    d['Transaction ' + str(i)]['Av_Stock_price_at_t0']
            i += 1

        # Enregistrer les données extraites dans un fichier JSON
        output_path = pdf_path.with_suffix('.json')
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(d, f, indent=4)

    def get_ticker_from_name(self, name): 
        if name in self.ticker_database:
            print('known', name)
            print(self.ticker_database[name]['ticker'])
            return self.ticker_database[name]['ticker'] 
        
        words = name.split(' ')
        ticker_counts = {}
        for i in range(1, len(words) + 1):
            partial_name = ' '.join(words[:i])
            try:
                result = search(partial_name)
                quotes = result.get('quotes', [])
                equity_quotes = [quote for quote in quotes if quote['quoteType'] == 'EQUITY']
                if equity_quotes:
                    symbols = []
                    for q in equity_quotes:
                        symbols.append(q['symbol'])
                    if any('.' not in symbol for symbol in symbols):
                        symbols = [symbol for symbol in symbols if '.' not in symbol]
                    else:
                        symbols = [symbol.split('.')[0] for symbol in symbols]
                    
                    for symbol in symbols:
                        if symbol in ticker_counts:
                            ticker_counts[symbol] += 1
                        else:
                            ticker_counts[symbol] = 1
            except:
                continue
        print('ticker_counts', ticker_counts)
        
        if ticker_counts:
            # Find the ticker that appears the most
            most_common_ticker = max(ticker_counts, key=ticker_counts.get)
            max_count = ticker_counts[most_common_ticker]
            
            # Check if there are multiple tickers with the same max count
            candidates = [ticker for ticker, count in ticker_counts.items() if count == max_count]
            if len(candidates) == 1:
                self.ticker_database[name] = { 'ticker' : candidates[0], 'isin' : 'NA'}
                self.save_ticker_database()
                return candidates[0]
            else:
                if max_count == 1:
                    best_match = max(candidates,
                        key=lambda ticker: fuzz.partial_ratio(name.lower(), ticker.lower()))
                    self.ticker_database[name] = { 'ticker' : best_match, 'isin' :'NA'}
                    self.save_ticker_database()
                    return best_match
                    
                else:
                    self.ticker_database[name] = { 'ticker' : candidates[0], 'isin' : 'NA'}
                    self.save_ticker_database()
                    return candidates[0]
        else:
            # self.ticker_database[name] = { 'ticker' : 'NA', 'isin' : 'NA'}
            # self.save_ticker_database()
            return 'NA'
                 
    def get_isin_from_ticker(self,name,ticker):
        if ticker=='NA':
            # print('No ticker found for', name)
            return 'NA'
        else:
            url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_KEY}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # print(data)
                if data:
                    info=data[0]  # Le profil de l'entreprise est le premier élément de la liste
                    self.ticker_database[name]['isin'] = info['isin']
                    self.save_ticker_database()
            return info['isin']
    
    @staticmethod
    def get_average_stock_price(ticker, date):
        if ticker!='NA':
            stock = yf.Ticker(ticker)
            start=datetime.strptime(date, "%Y-%m-%d")
            end=start + timedelta(days=1)
            end=end.strftime("%Y-%m-%d")
            historical_data = stock.history(start=start, end=end)

            if not historical_data.empty:
                average_price = round((historical_data['Open'][0] + historical_data['Close'][0]) / 2, 2)
                return average_price
            return None
        else:
            return None

    @staticmethod
    def identify_investment_type(description):
        # Définir les motifs pour différents types d'investissements
        patterns = {
            "Call Option": r"call options",
            "Put Option": r"put options",
            "Stock": r"shares|stocks",
            "Bond": r"bonds",
            # Ajoutez d'autres types d'investissements si nécessaire
        }
        
        for investment_type, pattern in patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                return investment_type
        return "Unknown"

    @staticmethod
    def get_option_price_one_week_ago_fmp(symbol, expiration_date, strike_price, option_type):

        # Calculer la date une semaine avant aujourd'hui
        one_week_ago = datetime.now() - timedelta(days=7)
        one_week_ago_str = one_week_ago.strftime("%Y-%m-%d")
        
        url = f'https://financialmodelingprep.com/api/v3/historical-options/{symbol}?from={one_week_ago_str}&to={one_week_ago_str}&apikey={FMP_KEY}'
        
        response = requests.get(url)
        data = response.json()
        
        for option in data:
            if option['expirationDate'] == expiration_date and option['strike'] == strike_price and option['type'].upper() == option_type.upper():
                return option['lastPrice']
        return None
    
    @staticmethod
    def extract_option_details(description):
        # Utiliser des expressions régulières pour extraire le strike price et la date d'expiration
        strike_pattern = r"strike price of \$(\d+)"
        expiration_pattern = r"expiration date of (\d{1,2}/\d{1,2}/\d{2,4})"
        
        strike_match = re.search(strike_pattern, description)
        expiration_match = re.search(expiration_pattern, description)
        
        if strike_match and expiration_match:
            strike_price = float(strike_match.group(1))
            expiration_date = datetime.strptime(expiration_match.group(1), "%m/%d/%y").strftime("%Y-%m-%d")
            return expiration_date, strike_price
        else:
            return None, None
