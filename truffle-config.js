// require('dotenv').config();
// const { MNEMONIC, PROJECT_ID } = process.env;
// const HDWalletProvider = require('@truffle/hdwallet-provider');

module.exports = {
  compilers: {
    solc: {
      version: "0.8.7", // This specifies the Solidity version
      settings: {
        optimizer: {
          enabled: true,  // This enables the optimizer
          runs: 200       // This sets the number of optimization runs
        },
        evmVersion: "istanbul" // This specifies the EVM version
      }
    }
  },
  mocha: {
    // timeout: 100000
  },
  // db: {
  //   enabled: false,
  //   host: "127.0.0.1",
  //   adapter: {
  //     name: "indexeddb",
  //     settings: {
  //       directory: ".db"
  //     }
  //   }
  // }
};
