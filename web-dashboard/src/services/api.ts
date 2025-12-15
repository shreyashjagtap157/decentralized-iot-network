import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Base API configuration
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

class ApiService {
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: API_URL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        // Response interceptor for error handling
        this.client.interceptors.response.use(
            (response) => response,
            (error) => {
                console.error('API Error:', error.response?.data?.detail || error.message);
                return Promise.reject(error);
            }
        );
    }

    // Generic request methods
    public async get<T>(url: string, params?: any): Promise<T> {
        const response: AxiosResponse<T> = await this.client.get(url, { params });
        return response.data;
    }

    public async post<T>(url: string, data?: any): Promise<T> {
        const response: AxiosResponse<T> = await this.client.post(url, data);
        return response.data;
    }

    // --- Staking API ---
    public async getStakingStats(): Promise<any> {
        return this.get('/staking/stats');
    }

    public async getUserStake(address: string): Promise<any> {
        return this.get(`/staking/user/${address}`);
    }

    public async stakeTokens(address: string, amount: number, lockDays: number): Promise<any> {
        return this.post('/staking/stake', { address, amount, lock_days: lockDays });
    }

    public async unstakeTokens(address: string, amount: number): Promise<any> {
        return this.post('/staking/unstake', { address, amount });
    }

    public async claimRewards(address: string): Promise<any> {
        return this.post(`/staking/claim/${address}`);
    }

    // --- Governance API ---
    public async getProposals(): Promise<any> {
        return this.get('/governance/proposals');
    }

    public async castVote(proposalId: number, address: string, support: number): Promise<any> {
        return this.post(`/governance/vote`, { proposal_id: proposalId, voter: address, support });
    }

    // --- Bridge API ---
    public async getBridgeChains(): Promise<any> {
        return this.get('/bridge/chains');
    }

    public async estimateBridgeFee(amount: number): Promise<any> {
        return this.get('/bridge/fee', { amount });
    }

    // --- NFT API ---
    public async getUserNFTs(address: string): Promise<any> {
        return this.get(`/nft/owner/${address}`);
    }
}

export const api = new ApiService();
