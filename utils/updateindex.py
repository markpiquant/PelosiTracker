"""
Created on Sunday Jan 13 00:23:00 2025
This scripts contains the UpdateIndex class used to create the index from the JSON containing congress trades
"""
# Standard library imports
# import csv, zipfile
# import requests
# import os
# import fitz # PyMuPDF
# import json
# import re
# import itertools
import yfinance as yf
from yahooquery import search
from fuzzywuzzy import fuzz

# personal imports
# from utils.Paths import PATH, DATAPATH

class UpdateIndex():
    def __init__(self):
        self.index = None
        self.companies = None
        self.trades = None
        self.positions = None
        self.index

    def create_index(self):
        self.index = self.companies
        return self.index

    