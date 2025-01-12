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
from yahooquery import search
from fuzzywuzzy import fuzz

# personal imports
from utils.Paths import PATH, DATAPATH

class GetData:
    def __init__(self, trader, year):
        self.trader = trader
        self.year = year

        self.zip_file_url = 'https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{}FD.ZIP'.format(self.year)
        self.pdf_file_url = 'https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{}/'.format(self.year)
        self.zipfile_name = '{}.zip'.format(self.year)
            
    def fetch_trades(self):
        """
        Fetches trade data for the specified trader and year.

        This function downloads a ZIP file containing financial disclosure PDFs,
        extracts the contents, and processes the relevant files for the specified
        trader. If 'all' traders are specified, it processes files for all traders.
        The function saves the PDFs to the appropriate directories and renames them
        based on the trader's name and the document ID. Finally, it removes the
        temporary ZIP, TXT, and XML files.

        Attributes:
            self.zip_file_url (str): URL to download the ZIP file.
            self.pdf_file_url (str): Base URL to download individual PDF files.
            self.zipfile_name (str): Name of the downloaded ZIP file.
            self.trader (str): Name of the trader or 'all' to process all traders.
            self.year (str): Year of the financial disclosures.
        """
        r = requests.get(self.zip_file_url)
        zipfile_name = '{}.zip'.format(self.year)

        with open(zipfile_name, 'wb') as f: # opens the file in write binary mode
            f.write(r.content)

        with zipfile.ZipFile(zipfile_name) as z: # opens the zip file
            z.extractall('.') # extracts all the files in the zip file to the current directory

        # Open File.txt
        with open('{}FD.txt'.format(self.year)) as f:
            i=0 # contains the number of files found for the trader
            reader = csv.reader(f, delimiter='\t')
            next(reader) # skip the header
            for line in reader:
                if self.trader =='all' or line[1] == self.trader: # if the trader is the one we are looking for
                    trader_name, doc_id = line[1], line[8]
                    name = line[2]+'_'+line[1]+'_'+line[7].replace('/','_')
                    r = requests.get(f"{self.pdf_file_url}{doc_id}.pdf")
                    
                    trader_path = DATAPATH / trader_name # code that creates a path to the trader's directory
                    os.makedirs(trader_path, exist_ok=True) # Ensure the directory for trader exists

                    pdf_path = os.path.join(trader_path, f"{name}.pdf")
                    with open(pdf_path, 'wb') as pdf_file:
                        pdf_file.write(r.content)
                    i+=1

        # Remove the .zip, .txt, and .xml files
        os.remove(zipfile_name)
        os.remove('{}FD.txt'.format(self.year))
        xml_filename = '{}FD.xml'.format(self.year)
        if os.path.exists(xml_filename):
            os.remove(xml_filename)

        print('======= Data fetched successfully =======')
        print('======= {} trade declarations founds for {} in {} ======='.format(i, self.trader, self.year))# code that prints the number of files in the DATAPATH directory

    def extract_trades_from_pdf(self):
        '''
        Pour tous les nouveaux fichiers téléchargés, on extrait les données des transactions et on les enregistre dans un fichier JSON.
        '''
        for trader_folder in DATAPATH.iterdir():# Parcourir chaque sous-dossier dans DATAPATH
            if trader_folder.is_dir():
                for pdf_file in trader_folder.glob("*.pdf"):# Parcourir chaque fichier PDF dans le sous-dossier
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
                start_index = next(i for i, line in enumerate(lines) if "Owner" in line)
                
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
        miniP, miniS = 0, 0 
        maxiP, maxiS = 0, 0 
        for elem in split_transactions[1:]:
            # Vérifier si l'élément contient 'S', 'P', 'S (partial)', ou 'P (partial)' comme mots complets
            if re.search(r'(.*?)(?<![./-])\b(S|P)\b(?![./-])|\bS \(partial\)\b|\bP \(partial\)\b', elem[0]):
                # Diviser l'élément en deux et reformater la liste
                match = re.search(r'(.*?)(?<![./-])\b(S|P)\b(?![./-])|\bS \(partial\)\b|\bP \(partial\)\b', elem[0])
                if match:
                    elem = [match.group(1).strip(), match.group(2)] + elem[1:]

            
            while elem[1] not in ['P','S','P (partial)','S (partial)', 'E']:
                elem=[elem[0]]+elem[2:]

            # Cleaning des dates
            if len(elem[2])==21:
                elem[2]=elem[2][:10]
            elif len(elem[2])==10:
                elem=elem[:3]+elem[4:]

            # cleaning des amounts
            if len(elem[3].split('-')[1])==0:
                elem[3]=elem[3].split('-')[0]+'- '+elem[4]
                elem=elem[:4]+elem[5:]

            # rangement des données dans un dictionnaire
            d['Transaction ' + str(i)] = {}
            d['Transaction ' + str(i)]['Company'] = elem[0]
            d['Transaction ' + str(i)]['Ticker']=GetData.get_ticker_from_name(elem[0])
            d['Transaction ' + str(i)]['Action'] = elem[1]
            d['Transaction ' + str(i)]['Date'] = elem[2]
            d['Transaction ' + str(i)]['Amount'] = elem[3]
            try:
                d['Transaction ' + str(i)]['Description'] = elem[5].replace("D\u0287\u0295\u0285\u0294\u028b\u0292\u0296\u028b\u0291\u0290: ", "")
            except IndexError:
                d['Transaction ' + str(i)]['Description'] = 'None'
            i += 1

            sep=elem[3].split(' - ')
            sep[0]=sep[0].split('$')[1].replace(',', '')
            sep[1]=sep[1].split('$')[1].replace(',', '')

            if elem[1][0] == 'P':
                miniP += int(sep[0])
                maxiP += int(sep[1])
            else:
                miniS += int(sep[0])
                maxiS += int(sep[1])
        d['Amount purchased'] = str(miniP) + ' - ' + str(maxiP)
        d['Amount sold'] = str(miniS) + ' - ' + str(maxiS)

        # Enregistrer les données extraites dans un fichier JSON
        output_path = pdf_path.with_suffix('.json')
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(d, f, indent=4)

        # print(f"Les données des transactions ont été extraites et enregistrées dans {output_path}")
    
    @staticmethod
    def get_ticker_from_name(name):
        try:
            # Recherche sur Yahoo Finance
            result = search(name)
            quotes = result.get('quotes', [])
            
            if quotes:
                # Appliquer un score de correspondance fuzzy pour chaque résultat
                best_match = max(
                    quotes,
                    key=lambda quote: fuzz.partial_ratio(name.lower(), quote['shortname'].lower())
                )
                
                # Seuil de correspondance acceptable (ajuster si nécessaire)
                if fuzz.partial_ratio(name.lower(), best_match['shortname'].lower()) > 20:
                    return best_match['symbol']
                else:
                    return "Aucun ticker correspondant trouvé avec un score suffisant."
            else:
                # print("Erreur lors de la recherche, tentative de recherche mot par mot")
                words = name.split(' ')
                for word in words:
                    try:
                        result = search(word)
                        quotes = result['quotes'][0]
                        return quotes['symbol']
                    except:
                        try:
                            result = search(word)
                            quotes = result.get('quotes', [])
                            if quotes:
                                best_match = max(
                                    quotes,
                                    key=lambda quote: fuzz.partial_ratio(word.lower(), quote['shortname'].lower())
                                )
                                if fuzz.partial_ratio(word.lower(), best_match['shortname'].lower()) > 20:
                                    return best_match['symbol']
                        except:
                            return "NA"
        except Exception as e:
            return f"Erreur lors de la recherche: {e}"