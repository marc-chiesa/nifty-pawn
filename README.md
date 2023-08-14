## README

This project requires Python (3.11.4 was used). It is recommended to install it in a virtual environment.

It uses Ape with Vyper to demonstrate an NFT pawning contract. Example NFT and ERC20 token contracts are also provided to demonstrate the end-to-end functionality and inter-contract communication.

All contracts are under the `contracts` directory.

- *NFT.vy*: a basic NFT contract, mostly taken from a tutorial provided by ApeWorx
- *Token.vy*: a basic ERC20 contract, also largely take from a tutorial
- *NiftyPawn*: The contract that provides lending, repayment, defaulting, and term cancelation. Uses the other two contracts for collateral and currency.

### Compiling
Contracts can be built with `ape compile`

### Tests
Tests can be run with `ape test`

### Setup
Users will need Python with the following packages installed from pip
- ape-geth
- ape-template
- eth-ape

Users will also need a few local accounts to serve the roles of borrower, lender, and contract owner (broker).

These can be created with

`ape accounts generate <account name>`

### Deploying
To deploy the contracts to the local chain, run the following:

`ape run deploy --network http://127.0.0.1:22000`

### Running scripts
Files in the scripts directory can be run on a local chain with the following format:

`ape run <script-base-name> --network http://127.0.0.1:<http port>`

e.g.

`ape run successful_lend --network http://127.0.0.1:22000`