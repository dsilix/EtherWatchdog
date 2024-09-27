import asyncio
import aiohttp
import os
import csv
import time
import pygame  # Used for playing audio
from colorama import Fore, Style, init  # For coloring terminal output

# Initialize colorama for colored output
init(autoreset=True)

# API and File Configuration
API_KEY = 'YOUR_API_KEY'  # Replace with your actual API key for Etherscan
BASE_URL = 'https://api.etherscan.io/api'  # Use the Etherscan endpoint for Ethereum

ADDRESS_DATABASE_FILE = 'address_database.csv'
TOP_TWENTY_FILE = 'top_twenty_balances.csv'
ALERT_SOUND_FILE = 'found.mp3'  # Replace with the name of your audio file

total_blocks_scanned = 0
total_contracts_detected = 0
contract_balances = {}  # Dictionary to store contract addresses and balances
last_balance_update_block = 0  # To track when balances were last updated

def load_addresses():
    """
    Loads addresses and their balances from a CSV file into a dictionary.
    """
    contract_balances = {}
    if os.path.exists(ADDRESS_DATABASE_FILE):
        with open(ADDRESS_DATABASE_FILE, mode='r') as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                if len(row) == 2:
                    address, balance = row
                    try:
                        contract_balances[address] = float(balance)
                    except ValueError:
                        print(f"Invalid balance for address {address}: {balance}")
    return contract_balances

def save_addresses(contract_balances):
    """
    Saves addresses and their balances from the dictionary to a CSV file.
    """
    with open(ADDRESS_DATABASE_FILE, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        for address, balance in contract_balances.items():
            writer.writerow([address, balance])

def save_top_twenty(top_twenty):
    """
    Saves the top 20 addresses and their balances to a separate CSV file.
    """
    with open(TOP_TWENTY_FILE, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        for address, balance in top_twenty:
            writer.writerow([address, balance])

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

async def cleanup_database():
    """
    Asynchronously removes addresses with zero balance from the database to reduce API calls.
    """
    global contract_balances
    while True:
        # Run every 24 hours
        await asyncio.sleep(24 * 60 * 60)
        contract_balances = {addr: bal for addr, bal in contract_balances.items() if bal > 0}
        save_addresses(contract_balances)
        print(Fore.CYAN + "[+] Database cleanup complete. Removed addresses with zero balance.")

class RateLimiter:
    def __init__(self, max_calls_per_second):
        self.interval = 1 / max_calls_per_second
        self.lock = asyncio.Lock()
        self.last_call = None

    async def wait(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            if self.last_call:
                elapsed = now - self.last_call
                wait_time = self.interval - elapsed
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self.last_call = asyncio.get_event_loop().time()

async def fetch(session, url, rate_limiter):
    """
    Fetch data from a given URL with rate limiting.
    """
    await rate_limiter.wait()
    async with session.get(url) as response:
        try:
            data = await response.json()
            return data
        except Exception as e:
            print(Fore.RED + f"Error parsing JSON response from {url}: {e}")
            text = await response.text()
            print(Fore.YELLOW + f"Response received: {text}")
            return None

async def get_latest_block_number(session, rate_limiter):
    """
    Gets the latest block number from the Ethereum blockchain.
    """
    url = f"{BASE_URL}?module=proxy&action=eth_blockNumber&apikey={API_KEY}"
    data = await fetch(session, url, rate_limiter)
    if data and 'result' in data:
        block_number_hex = data['result']
        try:
            return int(block_number_hex, 16)
        except ValueError:
            print(Fore.RED + f"Error parsing block number: {data}")
            return None
    else:
        print(Fore.RED + f"Error getting the latest block number: {data}")
        return None

async def get_block_by_number(session, rate_limiter, block_number):
    """
    Retrieve a block by its number.
    """
    block_number_hex = hex(block_number)
    url = (f"{BASE_URL}?module=proxy&action=eth_getBlockByNumber"
           f"&tag={block_number_hex}&boolean=true&apikey={API_KEY}")
    data = await fetch(session, url, rate_limiter)
    if data and 'result' in data:
        return data['result']
    else:
        print(Fore.RED + f"Error retrieving block {block_number}: {data}")
        return None

async def get_transaction_receipt(session, rate_limiter, tx_hash):
    """
    Get the transaction receipt for a given transaction hash.
    """
    url = (f"{BASE_URL}?module=proxy&action=eth_getTransactionReceipt"
           f"&txhash={tx_hash}&apikey={API_KEY}")
    data = await fetch(session, url, rate_limiter)
    if data and 'result' in data and data['result']:
        return data['result']
    else:
        print(Fore.RED + f"Error retrieving transaction receipt for {tx_hash}: {data}")
        return None

def is_contract_creation(tx):
    """
    Determines if a transaction is a contract creation.
    """
    return tx.get('to') is None or tx.get('to') in ('0x0', '0x0000000000000000000000000000000000000000')

async def process_block(session, rate_limiter, block):
    """
    Process a block to find and record new contract addresses.
    """
    global total_contracts_detected, contract_balances
    transactions = block.get('transactions', [])
    for tx in transactions:
        if is_contract_creation(tx):
            tx_hash = tx.get('hash')
            if tx_hash:
                receipt = await get_transaction_receipt(session, rate_limiter, tx_hash)
                if receipt and 'contractAddress' in receipt and receipt['contractAddress']:
                    contract_address = receipt['contractAddress']
                    if contract_address not in contract_balances:
                        contract_balances[contract_address] = 0  # Initialize balance to 0
                        total_contracts_detected += 1
                        # Add new address to file
                        with open(ADDRESS_DATABASE_FILE, mode='a', newline='') as csv_file:
                            writer = csv.writer(csv_file)
                            writer.writerow([contract_address, 0])

async def fetch_balances(session, rate_limiter, current_block):
    """
    Fetch and update balances of all stored contract addresses.
    Play sound if a balance >= 50 ETH is found.
    """
    global contract_balances, last_balance_update_block
    print(Fore.YELLOW + "\n[+] Fetching balances...")

    addresses = list(contract_balances.keys())
    balance_threshold = 50.0  # Threshold for playing sound
    batch_size = 20  # Maximum addresses per request
    for i in range(0, len(addresses), batch_size):
        batch_addresses = addresses[i:i+batch_size]
        address_list = ','.join(batch_addresses)
        url = (f"{BASE_URL}?module=account&action=balancemulti"
               f"&address={address_list}&tag=latest&apikey={API_KEY}")
        data = await fetch(session, url, rate_limiter)
        if data is None:
            print(Fore.RED + f"No data received from {url}")
            continue
        if data.get('status') != '1':
            print(Fore.RED + f"API Error: {data.get('message', 'No message')} - {data}")
            continue
        if 'result' in data:
            result = data['result']
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        address = item.get('account') or item.get('address')
                        if address is None:
                            print(Fore.RED + f"No 'account' or 'address' key in item: {item}")
                            continue
                        balance_str = item.get('balance')
                        if balance_str is None:
                            print(Fore.RED + f"No 'balance' key in item: {item}")
                            continue
                        try:
                            balance_wei = int(balance_str)
                        except ValueError:
                            print(Fore.RED + f"Invalid balance value for address {address}: {balance_str}")
                            continue
                            # Convert balance to ETH
                        balance = balance_wei / 1e18
                        previous_balance = contract_balances.get(address, 0)
                        contract_balances[address] = balance
                        # Check if balance exceeds the threshold
                        if balance >= balance_threshold and previous_balance < balance_threshold:
                            print(Fore.GREEN + f"[ALERT] Address {address} has a balance of {balance:.4f} ETH")
                            play_alert_sound()
                    else:
                        print(Fore.RED + f"Unexpected item type in result: {type(item)}; item: {item}")
            else:
                print(Fore.RED + f"Unexpected format in 'result': {result}")
        else:
            print(Fore.RED + f"No 'result' key in data: {data}")
    
    # Save updated balances to file
    save_addresses(contract_balances)

    # Update the last balance check block
    last_balance_update_block = current_block

def play_alert_sound():
    """
    Plays an alert sound using pygame.
    """
    try:
        pygame.mixer.init()  # Initialize pygame mixer
        pygame.mixer.music.load(ALERT_SOUND_FILE)  # Load the MP3 file
        pygame.mixer.music.play()  # Play the audio
    except Exception as e:
        print(Fore.RED + f"Error playing sound: {e}")

def print_summary(block_number):
    """
    Prints the summary of the top 20 contract addresses by balance.
    """
    clear_terminal()
    print(Fore.CYAN + f"Balances updated at block {last_balance_update_block}")  # Add this line to show balance update
    print(Fore.GREEN + f"New block detected, block number {block_number}")
    print(Fore.MAGENTA + "__________________________________________________")
    print(f"Total blocks scanned: {total_blocks_scanned}")
    print(f"Smart contracts detected: {total_contracts_detected}\n")
    print(Fore.CYAN + f"{'ADDRESS':<60} {'BALANCE (ETH)':>15}")
    print(Fore.MAGENTA + '-' * 75)

    # Load addresses and balances from file
    contract_balances = load_addresses()

    # Sort addresses by balance in descending order
    sorted_contracts = sorted(contract_balances.items(), key=lambda x: x[1], reverse=True)
    # Get top 20
    top_twenty = sorted_contracts[:20]

    # Save top 20 to file
    save_top_twenty(top_twenty)

    for addr, balance in top_twenty:
        print(f"{addr:<60} {balance:>15.4f}")

async def animate_scanning(stop_event):
    """
    Display an animation while scanning the blockchain.
    """
    states = ["Scanning the blockchain.", "Scanning the blockchain..", "Scanning the blockchain..."]
    idx = 0
    while not stop_event.is_set():
        print(Fore.GREEN + "\r" + states[idx % len(states)], end='', flush=True)
        idx += 1
        await asyncio.sleep(0.5)
    print("\r", end='')  # Clear the line when done

async def main():
    global total_blocks_scanned, contract_balances
    rate_limiter = RateLimiter(max_calls_per_second=5)
    # Load existing addresses
    contract_balances = load_addresses()
    async with aiohttp.ClientSession() as session:
        last_processed_block = await get_latest_block_number(session, rate_limiter)
        if last_processed_block is None:
            print(Fore.RED + "Failed to retrieve the latest block number. Exiting.")
            return

        # Start the cleanup task in the background
        cleanup_task = asyncio.create_task(cleanup_database())

        while True:
            latest_block = await get_latest_block_number(session, rate_limiter)
            if latest_block is not None and latest_block > last_processed_block:
                # Start the animation
                stop_event = asyncio.Event()
                animation_task = asyncio.create_task(animate_scanning(stop_event))

                for block_number in range(last_processed_block + 1, latest_block + 1):
                    total_blocks_scanned += 1
                    block = await get_block_by_number(session, rate_limiter, block_number)
                    if block is not None:
                        await process_block(session, rate_limiter, block)
                        last_processed_block = block_number

                    # Fetch balances every 25 blocks
                    if total_blocks_scanned % 25 == 0:
                        await fetch_balances(session, rate_limiter, last_processed_block)

                # Stop the animation and print the summary
                stop_event.set()
                await animation_task
                print_summary(last_processed_block)
            else:
                await asyncio.sleep(1)  # Wait for 1 second before checking again

if __name__ == '__main__':
    asyncio.run(main())
