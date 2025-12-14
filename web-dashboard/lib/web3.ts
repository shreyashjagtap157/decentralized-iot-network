import Web3 from 'web3';

// Network Compensation Contract ABI (simplified version based on actual contract)
const NETWORK_COMPENSATION_ABI = [
    {
        "inputs": [{ "name": "user", "type": "address" }],
        "name": "getUserEarnings",
        "outputs": [{ "name": "", "type": "uint256" }],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{ "name": "user", "type": "address" }],
        "name": "calculatePendingRewards",
        "outputs": [{ "name": "", "type": "uint256" }],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "claimRewards",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{ "name": "_amount", "type": "uint256" }],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
];

class Web3Service {
    private web3: Web3 | null = null;
    private contract: any = null;
    private account: string | null = null;

    constructor() {
        this.init();
    }

    async init() {
        if (typeof window !== 'undefined' && (window as any).ethereum) {
            this.web3 = new Web3((window as any).ethereum);
            const contractAddress = process.env.NEXT_PUBLIC_NETWORK_COMPENSATION_CONTRACT;

            if (contractAddress) {
                this.contract = new this.web3.eth.Contract(
                    NETWORK_COMPENSATION_ABI as any,
                    contractAddress
                );
            }
        }
    }

    async connectWallet(): Promise<string | null> {
        if (!this.web3) return null;

        try {
            // Request account access
            const accounts = await (window as any).ethereum.request({
                method: 'eth_requestAccounts',
            });

            this.account = accounts[0];
            return this.account;
        } catch (error) {
            console.error('Failed to connect wallet:', error);
            return null;
        }
    }

    async getUserEarnings(address: string): Promise<string> {
        if (!this.contract) {
            // Try to re-init or check
            if (this.web3) await this.init();
            if (!this.contract) return '0';
        }

        try {
            // Using calculatePendingRewards as primary source to match smart contract view
            const earnings = await this.contract.methods.calculatePendingRewards(address).call();
            if (!this.web3) return '0';
            return this.web3.utils.fromWei(earnings, 'ether');
        } catch (error) {
            console.error('Failed to get user earnings:', error);
            // Fallback or rethrow
            return '0';
        }
    }

    async withdrawEarnings(): Promise<string> {
        if (!this.contract || !this.account) {
            throw new Error('Web3 not initialized or wallet not connected');
        }

        try {
            // claimRewards claims all pending rewards
            const transaction = await this.contract.methods
                .claimRewards()
                .send({ from: this.account });

            return transaction.transactionHash;
        } catch (error) {
            console.error('Failed to withdraw earnings:', error);
            throw error;
        }
    }

    async getBalance(): Promise<string> {
        if (!this.web3 || !this.account) return '0';

        try {
            const balance = await this.web3.eth.getBalance(this.account);
            return this.web3.utils.fromWei(balance, 'ether');
        } catch (error) {
            console.error('Failed to get balance:', error);
            return '0';
        }
    }

    getAccount(): string | null {
        return this.account;
    }

    isConnected(): boolean {
        return this.account !== null && this.web3 !== null;
    }
}

export const web3Service = new Web3Service();
