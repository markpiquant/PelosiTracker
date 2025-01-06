"""
Created on Sunday Jan 05 20:23:00 2024
This module contains the main.py file. Execute this file to get the results
"""
# Standard library imports
import csv, zipfile
import requests
import os
import fitz # PyMuPDF
import json

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

    def extract_trades_from_pdf(self,pdf_path):

        # Chemin vers le fichier PDF
        pdf_path = DATAPATH / pdf_path

        # Ouvrir le document PDF
        doc = fitz.open(pdf_path)

        # Initialiser une liste pour stocker les données du tableau
        transactions = []

        # Parcourir chaque page du document
        for page in doc:
            # Rechercher le texte "Transactions" sur la page
            text_instances = page.search_for("Owner")
            
            # Si le texte "Transactions" est trouvé
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
        transactions=transactions[:transactions.index("* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.")]

        d, dc ={}, []
        i = 1
        miniP, miniS= 0, 0 
        maxiP, maxiS= 0, 0 
        for k in range(len(transactions)):
            if transactions[k]=='SP':
                d['Transaction '+str(i)]={}
                d['Transaction '+str(i)]['Company']=transactions[k+1]
                dc.append(transactions[k+1])
                d['Transaction '+str(i)]['Action']=transactions[k+3]
                d['Transaction '+str(i)]['Date']=transactions[k+4]
                d['Transaction '+str(i)]['Amount']=transactions[k+5] + ' ' + transactions[k+6]
                d['Transaction '+str(i)]['Description']=transactions[k+8].replace("D\u0287\u0295\u0285\u0294\u028b\u0292\u0296\u028b\u0291\u0290: ","")
                i+=1

                if transactions[k+3]=='P':
                    miniP+=int(transactions[k+5].split('$')[1].split(' -')[0].replace(',',''))
                    maxiP+=int(transactions[k+6].split('$')[1].replace(',',''))
                else:
                    miniS+=int(transactions[k+5].split('$')[1].split(' -')[0].replace(',',''))
                    maxiS+=int(transactions[k+6].split('$')[1].replace(',',''))
        d['Amount purchased']=  str(miniP) + ' - ' + str(maxiP)
        d['Amount sold']=  str(miniS) + ' - ' + str(maxiS)

        transactions=d

        # Enregistrer les données extraites dans un fichier JSON
        output_path = pdf_path.with_suffix('.json')
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(transactions, f, indent=4)

        print(f"Les données des transactions ont été extraites et enregistrées dans {output_path}")