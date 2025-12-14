/**
 * Utility functions for exporting data to various formats.
 */

interface ExportOptions {
    filename: string;
    headers?: string[];
}

/**
 * Export data to CSV format and trigger download.
 */
export function exportToCSV<T extends Record<string, any>>(
    data: T[],
    options: ExportOptions
): void {
    if (data.length === 0) {
        console.warn('No data to export');
        return;
    }

    const headers = options.headers || Object.keys(data[0]);

    const csvContent = [
        // Header row
        headers.join(','),
        // Data rows
        ...data.map(row =>
            headers.map(header => {
                const value = row[header];
                // Handle special cases
                if (value === null || value === undefined) return '';
                if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
                    return `"${value.replace(/"/g, '""')}"`;
                }
                if (value instanceof Date) {
                    return value.toISOString();
                }
                return String(value);
            }).join(',')
        )
    ].join('\n');

    downloadFile(csvContent, `${options.filename}.csv`, 'text/csv;charset=utf-8;');
}

/**
 * Export data to JSON format and trigger download.
 */
export function exportToJSON<T>(data: T, options: ExportOptions): void {
    const jsonContent = JSON.stringify(data, null, 2);
    downloadFile(jsonContent, `${options.filename}.json`, 'application/json');
}

/**
 * Helper function to trigger file download.
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}

/**
 * Format devices data for export.
 */
export function formatDevicesForExport(devices: any[]): Record<string, any>[] {
    return devices.map(device => ({
        'Device ID': device.device_id,
        'Type': device.device_type,
        'Status': device.status,
        'Owner Address': device.owner_address || 'N/A',
        'Location': device.location_lat && device.location_lng
            ? `${device.location_lat}, ${device.location_lng}`
            : 'N/A',
        'Data Transmitted (MB)': device.total_bytes
            ? (device.total_bytes / 1024 / 1024).toFixed(2)
            : '0',
        'Quality Score': device.quality_score || 'N/A',
        'Created At': device.created_at
    }));
}

/**
 * Format analytics data for export.
 */
export function formatAnalyticsForExport(analytics: any): Record<string, any>[] {
    const rows: Record<string, any>[] = [];

    // Summary row
    rows.push({
        'Metric': 'Total Earnings',
        'Value': analytics.totalEarnings || 0,
        'Unit': 'ETH'
    });
    rows.push({
        'Metric': 'Total Data Transmitted',
        'Value': analytics.totalBytes || 0,
        'Unit': 'Bytes'
    });
    rows.push({
        'Metric': 'Active Devices',
        'Value': analytics.activeDevices || 0,
        'Unit': 'Count'
    });
    rows.push({
        'Metric': 'Average Quality Score',
        'Value': analytics.averageQuality || 0,
        'Unit': 'Percentage'
    });

    return rows;
}

/**
 * Format transactions for export.
 */
export function formatTransactionsForExport(transactions: any[]): Record<string, any>[] {
    return transactions.map(tx => ({
        'Transaction ID': tx.id,
        'Device ID': tx.device_id,
        'Amount': tx.reward_amount,
        'Status': tx.status,
        'Blockchain TX': tx.blockchain_tx_hash || 'Pending',
        'Created At': tx.created_at
    }));
}
