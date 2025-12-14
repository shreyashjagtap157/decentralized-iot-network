/**
 * ESP32 Mesh Networking Header
 * Header file for mesh_network.cpp
 */

#ifndef MESH_NETWORK_H
#define MESH_NETWORK_H

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

// ==================== Configuration ====================

#define MESH_CHANNEL 1
#define MAX_PEERS 20
#define HEARTBEAT_INTERVAL 30000  // 30 seconds
#define PEER_TIMEOUT 120000       // 2 minutes
#define MAX_HOP_COUNT 5
#define MAX_DATA_SIZE 200

// ==================== Message Types ====================

enum MessageType {
    MSG_DISCOVERY = 0x01,
    MSG_HEARTBEAT = 0x02,
    MSG_DATA = 0x03,
    MSG_ROUTE_REQUEST = 0x04,
    MSG_ROUTE_REPLY = 0x05,
    MSG_ACK = 0x06
};

// ==================== Structures ====================

/**
 * Mesh peer information
 */
struct MeshPeer {
    uint8_t mac[6];           // MAC address
    int8_t rssi;              // Signal strength
    uint32_t lastSeen;        // Last seen timestamp
    uint8_t hopCount;         // Hops to reach this peer
    bool isGateway;           // Is this peer a gateway
    bool isActive;            // Is peer currently active
};

/**
 * Mesh message structure
 */
struct MeshMessage {
    uint8_t type;             // Message type
    uint8_t srcMac[6];        // Source MAC
    uint8_t dstMac[6];        // Destination MAC
    uint8_t hopCount;         // Current hop count
    uint16_t sequenceNum;     // Sequence number for deduplication
    uint16_t dataLen;         // Data length
    uint8_t data[MAX_DATA_SIZE]; // Payload
};

/**
 * Routing table entry
 */
struct RouteEntry {
    uint8_t destination[6];   // Destination MAC
    uint8_t nextHop[6];       // Next hop MAC
    uint8_t hopCount;         // Total hops
    uint32_t lastUpdated;     // Last update time
};

// ==================== Callback Types ====================

/**
 * Callback for received data
 * @param src Source MAC address
 * @param data Pointer to data
 * @param len Data length
 */
typedef void (*DataCallback)(uint8_t* src, uint8_t* data, uint16_t len);

// ==================== Public Functions ====================

/**
 * Initialize mesh networking
 * Must be called before any other mesh functions
 */
void initMesh();

/**
 * Main mesh loop - call in Arduino loop()
 * Handles heartbeats and peer management
 */
void meshLoop();

/**
 * Send data to a specific peer
 * @param dest Destination MAC address
 * @param data Data to send
 * @param len Data length (max MAX_DATA_SIZE)
 */
void sendData(uint8_t* dest, uint8_t* data, uint16_t len);

/**
 * Send discovery broadcast
 * Announces presence to nearby peers
 */
void sendDiscovery();

/**
 * Set callback for received data
 * @param callback Function to call when data is received
 */
void setDataCallback(DataCallback callback);

/**
 * Set gateway mode
 * Gateway nodes connect to the backend server
 * @param gateway True to enable gateway mode
 */
void setGatewayMode(bool gateway);

/**
 * Get current peer count
 * @return Number of known peers
 */
int getPeerCount();

/**
 * Get nearest gateway peer
 * @return Pointer to nearest gateway or nullptr
 */
MeshPeer* getNearestGateway();

// ==================== Internal Functions ====================

// These are implemented in mesh_network.cpp
void sendBroadcast(MeshMessage* msg);
void sendUnicast(uint8_t* dest, MeshMessage* msg);
void sendHeartbeat();
void processMessage(MeshMessage* msg);
void handleDiscovery(MeshMessage* msg);
void handleData(MeshMessage* msg);
void handleRouteRequest(MeshMessage* msg);
void handleRouteReply(MeshMessage* msg);
int findPeer(uint8_t* mac);
int addPeer(uint8_t* mac, int8_t rssi, uint8_t hopCount, bool isGateway);
void removeStalePeers();
RouteEntry* findRoute(uint8_t* dest);
void updateRoute(uint8_t* dest, uint8_t* nextHop, uint8_t hopCount);

// ==================== Utility Macros ====================

/**
 * Compare two MAC addresses
 */
#define MAC_EQUAL(a, b) (memcmp(a, b, 6) == 0)

/**
 * Copy MAC address
 */
#define MAC_COPY(dst, src) memcpy(dst, src, 6)

/**
 * Print MAC address to serial
 */
#define MAC_PRINT(mac) \
    Serial.printf("%02X:%02X:%02X:%02X:%02X:%02X", \
        mac[0], mac[1], mac[2], mac[3], mac[4], mac[5])

#endif // MESH_NETWORK_H
