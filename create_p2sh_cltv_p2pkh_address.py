import argparse
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.transactions import Sequence
from bitcoinutils.keys import P2shAddress, PrivateKey, PublicKey
from bitcoinutils.script import Script
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK

def main():
    # always remember to setup the network
    setup("regtest")

    # parse the command-line arguments
    parser = argparse.ArgumentParser(description="Create a P2SH address with timelock.")
    parser.add_argument("public_key", help="The public key in HEX format")
    parser.add_argument("lock_time", type=int, help="The UNIX timestamp for the timelock")

    # parse the arguments
    args = parser.parse_args()

    # take the public key
    public_key = args.public_key.strip()

    # get the corresponding public key and address
    pub = PublicKey.from_hex(public_key)
    p2pkh_addr = pub.get_address()

    # take the absolute timelock
    lock_time = args.lock_time

    # create the redeem script
    redeem_script = Script(
        [
            lock_time,
            "OP_CHECKLOCKTIMEVERIFY",
            "OP_DROP",
            "OP_DUP",
            "OP_HASH160",
            p2pkh_addr.to_hash160(),
            "OP_EQUALVERIFY",
            "OP_CHECKSIG",
        ]
    )

    # create a P2SH address from a redeem script
    addr = P2shAddress.from_script(redeem_script)
    print("\nP2SH Address:", addr.to_string())

    print("\n--------------------------------------\n")

if __name__ == "__main__":
    main()