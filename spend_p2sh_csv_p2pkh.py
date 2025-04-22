import json
import argparse
import requests
import subprocess
from bitcoinutils.setup import setup
from bitcoinutils.script import Script
from ecdsa import SigningKey, SECP256k1
from bitcoinutils.utils import to_satoshis
from ecdsa.util import sigencode_der_canonize
from bitcoinutils.keys import P2pkhAddress, PrivateKey, P2shAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput

def get_utxos(address):
    """ returns UTXOs for a specific address """
    try:
        cmd = ["bitcoin-cli", "-regtest", "listunspent", "0", "9999999", f'["{address}"]']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting UTXOs: {str(e)}")
        return []

def get_fee_rate():
    """ Get the fee rate from an external API. """
    try:
        response = requests.get("https://mempool.space/api/v1/fees/recommended", verify=r'C:\Users\User\AppData\Local\Programs\Python\Python312\Lib\site-packages\certifi\cacert.pem')
        fee_data = response.json()
        fee_rate = fee_data.get("feerate")
        if fee_rate is not None:
            return fee_rate
    except Exception as e:
        print(f"Error getting fee rate: {e}")

    return 10  # Default fee rate (sat/byte)

def precompute_constants(utxos, fee_rate, to_address):
    """ Precompute the constants for the transaction """
    # Calculate the total input amount
    total_input = sum([utxo['amount'] for utxo in utxos])
    total_input_satoshis = to_satoshis(total_input)

    # Determine the output amount
    output_amount_satoshis = total_input_satoshis - (fee_rate * 192)

    # Create the output
    to_address_p2pkh = P2pkhAddress(to_address)
    tx_output = TxOutput(output_amount_satoshis, to_address_p2pkh.to_script_pub_key())

    # Now we can create the transaction inputs and outputs
    sequence = (0xfffffffe).to_bytes(4, byteorder='little')
    tx_inputs = [TxInput(utxo['txid'], utxo['vout'], sequence=sequence) for utxo in utxos]
    tx_outputs = [tx_output]

    # Precompute the tx size with inputs and outputs
    input_size = 148 * len(tx_inputs)
    output_size = 34 * len(tx_outputs)
    tx_size = 10 + input_size + output_size

    # Calculate the base fee
    fee = tx_size * fee_rate

    #print(f"\nPrecomputed Constants:")
    #print(f"Total Input Amount (satoshis): {total_input_satoshis}")
    #print(f"Output Amount (satoshis): {output_amount_satoshis}")
    #print(f"Transaction Size (bytes): {tx_size}")
    #print(f"Fee (satoshis): {fee}")
    return tx_inputs, tx_outputs, fee

def main():
    # always remember to setup the network
    setup("regtest")

    # parse the command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("p2sh_address")
    parser.add_argument("private_key")
    parser.add_argument("to_address")
    parser.add_argument("lock_time", type=int)
    args = parser.parse_args()

    # 1) Fetch UTXO
    utxos = get_utxos(args.p2sh_address)
    if not utxos:
        raise ValueError("No UTXOs found for address!")

    # 3) Calculate fee
    fee_rate = get_fee_rate()

    # 4) Create the redeem script - needed to sign the transaction
    p2pkh_sk = PrivateKey(args.private_key)
    p2pkh_addr = p2pkh_sk.get_public_key().get_address()
    redeem_script = Script(
        [
            args.lock_time,
            "OP_CHECKLOCKTIMEVERIFY",
            "OP_DROP",
            "OP_DUP",
            "OP_HASH160",
            p2pkh_addr.to_hash160(),
            "OP_EQUALVERIFY",
            "OP_CHECKSIG",
        ]
    )

    # 5) Send/spend to another address
    tx_inputs, tx_outputs, fee = precompute_constants(utxos, fee_rate, args.to_address)
    #print(f"\nTransaction Inputs: {tx_inputs}")
    #print(f"Transaction Outputs: {tx_outputs}")
    #print(f"Transaction Fee: {fee} satoshis")

    # 6) Create the transaction with locktime
    locktime_bytes = args.lock_time.to_bytes(4, 'little')
    tx = Transaction(tx_inputs, tx_outputs, locktime_bytes)
    print(f"Raw unsigned transaction: {tx.serialize()}")

    # Sign each input
    for i, tx_input in enumerate(tx.inputs):
        sh = tx.get_transaction_digest(i, redeem_script)
        # Set the scriptSig (unlocking script) -- unlock the P2PKH (sig, pk) plus
        # The redeem script, since it is a P2SH
        raw_priv = p2pkh_sk.to_bytes()
        sk = SigningKey.from_string(raw_priv, curve=SECP256k1)

        # Sign the transaction digest
        der_sig = sk.sign_digest(sh, sigencode=sigencode_der_canonize)
        sig = der_sig + b'\x01'

        # Create scriptSig with signature, public key and redeem script
        script_sig = Script([
            sig.hex(),
            p2pkh_sk.get_public_key().to_hex(),
            redeem_script.to_hex()
        ])
        tx.inputs[i].script_sig = script_sig
    # Print raw signed transaction ready to be broadcasted
    print(f"\nRaw signed transaction:" + tx.serialize())
    print(f"TXID: {tx.get_txid()}")

    # 7) Validates the transaction from bitcoin
    validate = subprocess.run(["bitcoin-cli", "-regtest", "testmempoolaccept", f'["{tx.serialize()}"]'], capture_output=True, text=True)
    result = json.loads(validate.stdout)

    if not result[0]['allowed']:
        print("Transaction failed:", result[0].get('reject-reason', 'Unknown reason'))
    else:
        try:
            txid = subprocess.run(["bitcoin-cli", "-regtest", "sendrawtransaction", tx.serialize()], capture_output=True, text=True).stdout.strip()
            print("\nTransaction broadcasted! TXID:", txid)
        except Exception as e:
            print(f"Error broadcasting transaction: {e}")

    print("\n--------------------------------------\n")

if __name__ == "__main__":
    main()