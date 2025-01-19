# Notes on the data

Note "slack Technologies, Inc. Class a": {
        "ticker": "CRM",
        "isin": "US71989C1099"
    },
Here, the ticker of slack was WORK but since the company was acquired by Salesforce, the ticker changed to CRM


Update 19/01/2025: 


Code now handles cases where ticker changed.
Code now handles cases where the identifiers used to separate trades are not consistent.
Code now update on the aggregated trades for each congressmen
- now we dinstinguish between stock and options
- we now have an estimate of real position using the descriptions in order to create indexes
