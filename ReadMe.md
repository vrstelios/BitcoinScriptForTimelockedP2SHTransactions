# Running the Python Scripts for Timelocked P2SH Transactions

This guide explains how to execute the Python scripts for creating and spending timelocked P2SH addresses, based on the steps outlined in the `e2e_execution.sh` file. Alternatively, you can directly execute the `./e2e_execution.sh` file, which will perform the following steps.

## Prerequisites

### Bitcoin Core Setup
- Ensure Bitcoin Core is installed and configured for regtest mode.
- Start the `bitcoind` daemon in regtest mode.

### Python Environment
- Use Python 3.12.6
- Install the required dependencies listed in `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```
- Activate the Python environment where the dependencies are installed.

### Reset Regtest Directory (Optional)
- Delete the `~/.bitcoin/regtest` directory to reset the blockchain state.
- Ensure `~/.bitcoin/bitcoin.conf` contains the following configuration:
  ```
  regtest=1
  server=1
  deprecatedrpc=create_bdb  # This option will be deprecated soon

  [regtest]
  maxtxfee=0.01
  fallbackfee=0.001
  ```

## Steps to Run the Scripts

### 1. Create a Legacy Wallet and Address
Run the following commands to create a wallet and generate a legacy address:
```bash
bitcoin-cli -regtest createwallet "wallet" false false "" false false
send_from_address=$(bitcoin-cli -regtest getnewaddress)
```

### 2. Mine Initial Blocks
Mine 101 blocks to unlock the coinbase rewards:
```bash
bitcoin-cli -regtest generatetoaddress 101 "$send_from_address"
```
Check the current balance:
```bash
current_balance=$(bitcoin-cli -regtest getbalance)
echo "Current balance: $current_balance"
```

### 3. Create a Timelocked P2SH Address
Run the `create_p2sh_cltv_p2pkh_address.py` script to generate a timelocked P2SH address:
```bash
python create_p2sh_cltv_p2pkh_address.py --key <private_key> --locktime <locktime>
```
- Replace `<private_key>` with the WIF private key.
- Replace `<locktime>` with the desired absolute locktime (UNIX timestamp).

### 4. Fund the Timelocked Address
Send funds to the generated P2SH address and mine a block to confirm:
```bash
bitcoin-cli -regtest sendtoaddress <timelocked_address> 1.0
bitcoin-cli -regtest generatetoaddress 1 "$send_from_address"
```
Repeat this step as needed to send multiple transactions.

Mine 10 additional blocks:
```bash
bitcoin-cli -regtest generatetoaddress 10 "$send_from_address"
```

### 5. Verify Block Count
Check the current block count to ensure it is less than the locktime:
```bash
block_count=$(bitcoin-cli -regtest getblockcount)
echo "Current block count: $block_count"
```

### 6. Create a Destination Wallet and Address
Create a destination wallet and generate a legacy address:
```bash
bitcoin-cli -regtest createwallet "dest_wallet" false false "" false false
destination_address=$(bitcoin-cli -regtest -rpcwallet=dest_wallet getnewaddress "" legacy)
```

### 7. Attempt to Spend from the Timelocked Address (Before Timelock)
Run the `spend_p2sh_csv_p2pkh.py` script to attempt spending from the timelocked address:
```bash
python ./spend_p2sh_csv_p2pkh.py --p2sh_address "$timelocked_address" --private_key "$private_key" --destination_p2pkh_address $destination_address --locktime $locktime
```
This transaction will be rejected because the timelock has not yet been reached.

### 8. Mine Blocks to Satisfy the Timelock
Mine blocks until the timelock is satisfied:
```bash
bitcoin-cli -regtest generatetoaddress $locktime "$send_from_address"
```

### 9. Spend from the Timelocked Address (After Timelock)
Run the `spend_p2sh_csv_p2pkh.py` script again to spend from the timelocked address:
```bash
python ./spend_p2sh_csv_p2pkh.py --p2sh_address "$timelocked_address" --private_key "$private_key" --destination_p2pkh_address $destination_address --locktime $locktime
```

### 10. Verify the Transaction
Check the mempool to ensure the transaction is broadcasted:
```bash
bitcoin-cli -regtest getrawmempool
```
Mine one more block to confirm the transaction:
```bash
bitcoin-cli -regtest generatetoaddress 1 "$send_from_address"
```

### 11. Check the Destination Address Balance
Verify the balance of the destination address:
```bash
bitcoin-cli -regtest scantxoutset start "[\"addr($destination_address)\"]"
```

## Notes
- Replace placeholders (e.g., `<private_key>`, `<timelocked_address>`) with actual values.
- Ensure the `bitcoin-cli` commands are executed in the same environment as the `bitcoind` daemon.