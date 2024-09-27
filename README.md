# EtherWatchdog
An Ethereum blockchain scanner that monitors and fetches smart contract balances. Optimized to stay within the 100,000 API call limit of the free Etherscan plan-
This Python-based blockchain scanner is your secret weapon for keeping an eye on Ethereum smart contracts and their balances. By continuously scanning blocks and fetching contract balances, it ensures you're always in the loop — like having eyes everywhere.

What's the purpose of the program?
Ever wish you could watch the Ethereum blockchain 24/7 without ever missing a beat? This scanner is designed to do exactly that — it tracks new smart contract creations and monitors their balances, automatically triggering an alert when a contract holds more than 50 ETH. It's like having a dedicated spy on the Ethereum blockchain, always watching, always vigilant (without needing any caffeine).

Features
Block Scanning: Scans Ethereum blocks in real-time to detect new smart contract creation transactions.
Balance Monitoring: Automatically fetches balances of stored contracts every 25 blocks, keeping API usage efficient and staying within the free plan's daily limit of 100,000 API calls on Etherscan.
Sound Alert: Plays an alert sound (found.mp3) when a smart contract balance exceeds 50 ETH. You’ll never miss a jackpot contract again.
Automated Cleanup: Removes contract addresses with zero balance every 24 hours to further optimize API usage.
Top Contracts Summary: Displays the top 20 smart contracts by balance after every balance update.
Requirements
Python 3.8+

Python Packages: Install the required packages by running the following command:
```
pip install aiohttp pygame
```
Etherscan API Key: You'll need an API key from Etherscan to query the blockchain. Be sure to replace the placeholder in the script with your own API key.

Installation and Setup
Clone the repository:
```
git clone https://github.com/dsilix/EtherWatchdog.git
```
```
cd EtherWatchdog
```
Install the required Python packages:
```
pip install aiohttp pygame
```
Add your Etherscan API key:

Open the script file and replace ```API_KEY = 'YOUR_API_KEY'``` with your actual Etherscan API key.
Ensure the sound file (found.mp3) is in the project directory. This sound will play when a smart contract hits the 50 ETH balance threshold.

# Usage
To start scanning Ethereum blocks and monitoring smart contract balances, run the Python script:
```python main.py```
The script will monitor new blocks, track smart contract creations, and periodically check contract balances.
It fetches balances every 25 blocks, keeping you within Etherscan’s free tier of 100,000 API calls per day.
When a contract balance exceeds 50 ETH, the found.mp3 sound will play.

# File Descriptions

main.py: The main Python script that handles block scanning, transaction processing, and balance checking.
address_database.csv: A CSV file that stores smart contract addresses and their current balances.
top_twenty_balances.csv: A CSV file that stores the top 20 smart contract addresses by balance after each update.
found.mp3: The alert sound that plays when a balance threshold is met (included in the repository).
# Customization
Balance Threshold: To change the balance threshold for triggering the alert sound (default: 50 ETH), modify the ```balance_threshold``` variable in the script.
Block Interval for Balance Checking: The script checks balances every 25 blocks. You can adjust this interval in the main loop.
