import os
import time
import requests
import smtplib
from web3 import Web3
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from web3.middleware import geth_poa_middleware

# Load environment variables
load_dotenv()

# Connect to Ethereum node
w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_URL')))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Set contract addresses and ABI
flashloan_contract_address = os.getenv('FLASHLOAN_CONTRACT_ADDRESS')
flashloan_contract_abi = os.getenv('FLASHLOAN_CONTRACT_ABI')
dai_address = '0x6B175474E89094C44Da98b954EedeAC495271d0F'
usdc_address = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
uniswap_pair_abi = os.getenv('UNISWAP_PAIR_ABI')
sushiswap_pair_abi = os.getenv('SUSHISWAP_PAIR_ABI')
UNISWAP_PAIR_ADDRESS = os.getenv('UNISWAP_PAIR_ADDRESS')
SUSHISWAP_PAIR_ADDRESS = os.getenv('SUSHISWAP_PAIR_ADDRESS')

# Set contract instances
flashloan_contract = w3.eth.contract(address=flashloan_contract_address, abi=flashloan_contract_abi)
dai_contract = w3.eth.contract(address=dai_address, abi=flashloan_contract_abi)
usdc_contract = w3.eth.contract(address=usdc_address, abi=flashloan_contract_abi)

# Constants
MAX_SLIPPAGE = 0.01  # 1%
BALANCE_THRESHOLD = 1 * 10**18  # 1 token

# SMTP settings
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Email settings
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
EMAIL_SUBJECT = 'Arbitrage Alert'

# Send email
def send_email(subject, message):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    server = smtplib.SMTP(host=SMTP_SERVER, port=SMTP_PORT)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()

# Get price on Uniswap
def get_price_uniswap(token0, token1):
    uniswap_pair = w3.eth.contract(address=UNISWAP_PAIR_ADDRESS, abi=uniswap_pair_abi)
    reserve0, reserve1, _ = uniswap_pair.functions.getReserves().call()
    price = reserve1 / reserve0
    return price

# Get price on Sushiswap
def get_price_sushiswap(token0, token1):
    sushiswap_pair = w3.eth.contract(address=SUSHISWAP_PAIR_ADDRESS, abi=sushiswap_pair_abi)
    reserve0, reserve1, _ = sushiswap_pair.functions.getReserves().call()
    price = reserve1 / reserve0
    return price

# Real-time data monitoring
def monitor_prices():
    dai_usdc_uniswap = get_price_uniswap(dai_address, usdc_address)
    dai_usdc_sushiswap = get_price_sushiswap(dai_address, usdc_address)
    return dai_usdc_uniswap, dai_usdc_sushiswap

# Gas price optimization
def get_gas_price():
    response = requests.get('https://ethgasstation.info/api/ethgasAPI.json')
    gas_price_data = response.json()
    gas_price_gwei = gas_price_data['fast'] / 10
    gas_price_wei = w3.toWei(gas_price_gwei, 'gwei')
    return gas_price_wei

# Arbitrage profitability calculation
def calculate_profitability():
    dai_usdc_uniswap, dai_usdc_sushiswap = monitor_prices()
    profitability = dai_usdc_sushiswap - dai_usdc_uniswap - get_gas_price()  # Subtract the gas price
    return profitability

# Risk management
def check_risk_limits():
    MINIMUM_PROFITABILITY = 0.01  # Minimum profitability in ETH
    profitability = calculate_profitability()
    if profitability < MINIMUM_PROFITABILITY:
        return False
    return True

# Trigger flash loan and arbitrage trade
def trigger_arbitrage_trade():
    nonce = w3.eth.getTransactionCount(os.getenv('ADDRESS'))
    amount = 1000 * 10**18  # 1000 DAI
    txn_dict = flashloan_contract.functions.initiateFlashloan(amount).buildTransaction({
        'chainId': 1,
        'gas': 1500000,
        'gasPrice': get_gas_price(),
        'nonce': nonce,
    })
    signed_txn = w3.eth.account.signTransaction(txn_dict, os.getenv('PRIVATE_KEY'))
    result = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(result)
    print(f"Initiated flash loan. Transaction receipt: {tx_receipt}")

# Slippage calculation
def calculate_slippage(amount_in, reserve_in, reserve_out):
    amount_out_expected = (amount_in * reserve_out) / reserve_in
    amount_out_real = (amount_in * 0.997 * reserve_out) / (reserve_in + amount_in * 0.997)
    slippage = abs((amount_out_expected - amount_out_real) / amount_out_expected)
    return slippage

# Adjust trade volume
def adjust_trade_volume(amount_in, reserve_in, reserve_out):
    slippage = calculate_slippage(amount_in, reserve_in, reserve_out)
    while slippage > MAX_SLIPPAGE:
        amount_in *= 0.99
        slippage = calculate_slippage(amount_in, reserve_in, reserve_out)
    return amount_in

# Balance Monitoring
def monitor_balance():
    balance = dai_contract.functions.balanceOf(flashloan_contract_address).call()
    if balance > BALANCE_THRESHOLD:
        print(f"Balance exceeded threshold: {balance}")
        send_email(EMAIL_SUBJECT, f"Balance exceeded threshold: {balance}")

# Health Checks
def perform_health_check():
    try:
        block = w3.eth.blockNumber
        print(f"Health check passed. Current block: {block}")
    except Exception as e:
        print(f"Health check failed. Error: {e}")
        send_email(EMAIL_SUBJECT, f"Health check failed. Error: {e}")

# Main function
def main():
    while True:
        dai_usdc_uniswap, dai_usdc_sushiswap = monitor_prices()
        if dai_usdc_uniswap < dai_usdc_sushiswap:
            print('Arbitrage opportunity detected')
            send_email(EMAIL_SUBJECT, 'Arbitrage opportunity detected')
            gas_price = get_gas_price()
            profitability = calculate_profitability()
            if check_risk_limits():
                print('Risk limits exceeded')
                send_email(EMAIL_SUBJECT, 'Risk limits exceeded')
                continue
            trigger_arbitrage_trade()
        monitor_balance()
        perform_health_check()
        time.sleep(10)  # Sleep for 10 seconds before checking again

# Run the script
if __name__ == '__main__':
    main()
