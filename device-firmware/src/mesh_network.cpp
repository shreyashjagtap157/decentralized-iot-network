/**
 * ESP32 Mesh Networking Firmware
 * Enables device-to-device communication for decentralized network.
 * 
 * Uses ESP-NOW for low-latency mesh communication.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// ==================== Configuration ====================

#define MESH_CHANNEL 1
#define MAX_PEERS 20
#define HEARTBEAT_INTERVAL 30000  // 30 seconds
#define PEER_TIMEOUT 120000       // 2 minutes

// Message types
enum MessageType {
    MSG_DISCOVERY = 0x01,
    MSG_HEARTBEAT = 0x02,
    MSG_DATA = 0x03,
    MSG_ROUTE_REQUEST = 0x04,
    MSG_ROUTE_REPLY = 0x05,
    MSG_ACK = 0x06
};

// ==================== Structures ====================

struct MeshPeer {
    uint8_t mac[6];
    int8_t rssi;
    uint32_t lastSeen;
    uint8_t hopCount;
    bool isGateway;
    bool isActive;
};

struct MeshMessage {
    uint8_t type;
    uint8_t srcMac[6];
    uint8_t dstMac[6];
    uint8_t hopCount;
    uint16_t sequenceNum;
    uint16_t dataLen;
    uint8_t data[200];
};

struct RouteEntry {
    uint8_t destination[6];
    uint8_t nextHop[6];
    uint8_t hopCount;
    uint32_t lastUpdated;
};

// ==================== Global Variables ====================

uint8_t myMac[6];
char deviceId[32];
MeshPeer peers[MAX_PEERS];
int peerCount = 0;

RouteEntry routingTable[MAX_PEERS];
int routeCount = 0;

uint16_t sequenceNumber = 0;
bool isGateway = false;
uint32_t lastHeartbeat = 0;

// Callbacks
typedef void (*DataCallback)(uint8_t* src, uint8_t* data, uint16_t len);
DataCallback onDataReceived = nullptr;

// ==================== Function Declarations ====================

void initMesh();
void sendDiscovery();
void sendHeartbeat();
void sendData(uint8_t* dest, uint8_t* data, uint16_t len);
void processMessage(MeshMessage* msg);
int findPeer(uint8_t* mac);
int addPeer(uint8_t* mac, int8_t rssi, uint8_t hopCount, bool isGateway);
void removeStalePeers();
RouteEntry* findRoute(uint8_t* dest);
void updateRoute(uint8_t* dest, uint8_t* nextHop, uint8_t hopCount);

// ==================== ESP-NOW Callbacks ====================

void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
    if (status != ESP_NOW_SEND_SUCCESS) {
        Serial.println("[MESH] Send failed");
    }
}

void onDataRecv(const uint8_t *mac, const uint8_t *data, int len) {
    if (len < sizeof(MeshMessage) - 200) return;
    
    MeshMessage msg;
    memcpy(&msg, data, len);
    
    processMessage(&msg);
}

// ==================== Initialization ====================

void initMesh() {
    // Get MAC address
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    esp_wifi_get_mac(WIFI_IF_STA, myMac);
    
    snprintf(deviceId, sizeof(deviceId), "ESP32_%02X%02X%02X%02X",
        myMac[2], myMac[3], myMac[4], myMac[5]);
    
    Serial.printf("[MESH] Device ID: %s\n", deviceId);
    Serial.printf("[MESH] MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
        myMac[0], myMac[1], myMac[2], myMac[3], myMac[4], myMac[5]);
    
    // Set WiFi channel
    esp_wifi_set_channel(MESH_CHANNEL, WIFI_SECOND_CHAN_NONE);
    
    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("[MESH] ESP-NOW init failed");
        return;
    }
    
    esp_now_register_send_cb(onDataSent);
    esp_now_register_recv_cb(onDataRecv);
    
    // Add broadcast peer
    esp_now_peer_info_t broadcastPeer;
    memset(&broadcastPeer, 0, sizeof(broadcastPeer));
    memset(broadcastPeer.peer_addr, 0xFF, 6);
    broadcastPeer.channel = MESH_CHANNEL;
    broadcastPeer.encrypt = false;
    esp_now_add_peer(&broadcastPeer);
    
    Serial.println("[MESH] Initialized");
    
    // Send initial discovery
    sendDiscovery();
}

// ==================== Message Sending ====================

void sendBroadcast(MeshMessage* msg) {
    uint8_t broadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    uint16_t msgLen = sizeof(MeshMessage) - 200 + msg->dataLen;
    esp_now_send(broadcast, (uint8_t*)msg, msgLen);
}

void sendUnicast(uint8_t* dest, MeshMessage* msg) {
    // Check if peer exists
    esp_now_peer_info_t peer;
    if (esp_now_get_peer(dest, &peer) != ESP_OK) {
        // Add peer
        memset(&peer, 0, sizeof(peer));
        memcpy(peer.peer_addr, dest, 6);
        peer.channel = MESH_CHANNEL;
        peer.encrypt = false;
        esp_now_add_peer(&peer);
    }
    
    uint16_t msgLen = sizeof(MeshMessage) - 200 + msg->dataLen;
    esp_now_send(dest, (uint8_t*)msg, msgLen);
}

void sendDiscovery() {
    MeshMessage msg;
    msg.type = MSG_DISCOVERY;
    memcpy(msg.srcMac, myMac, 6);
    memset(msg.dstMac, 0xFF, 6);
    msg.hopCount = 0;
    msg.sequenceNum = sequenceNumber++;
    msg.dataLen = 1;
    msg.data[0] = isGateway ? 1 : 0;
    
    sendBroadcast(&msg);
    Serial.println("[MESH] Discovery sent");
}

void sendHeartbeat() {
    MeshMessage msg;
    msg.type = MSG_HEARTBEAT;
    memcpy(msg.srcMac, myMac, 6);
    memset(msg.dstMac, 0xFF, 6);
    msg.hopCount = 0;
    msg.sequenceNum = sequenceNumber++;
    
    // Include peer count and gateway status
    msg.dataLen = 2;
    msg.data[0] = peerCount;
    msg.data[1] = isGateway ? 1 : 0;
    
    sendBroadcast(&msg);
}

void sendData(uint8_t* dest, uint8_t* data, uint16_t len) {
    if (len > 200) len = 200;
    
    MeshMessage msg;
    msg.type = MSG_DATA;
    memcpy(msg.srcMac, myMac, 6);
    
    // Find route to destination
    RouteEntry* route = findRoute(dest);
    uint8_t* nextHop = dest;
    
    if (route != nullptr) {
        nextHop = route->nextHop;
    }
    
    memcpy(msg.dstMac, dest, 6);
    msg.hopCount = 0;
    msg.sequenceNum = sequenceNumber++;
    msg.dataLen = len;
    memcpy(msg.data, data, len);
    
    sendUnicast(nextHop, &msg);
}

// ==================== Message Processing ====================

void processMessage(MeshMessage* msg) {
    // Check if from self
    if (memcmp(msg->srcMac, myMac, 6) == 0) return;
    
    // Update peer info
    int peerIdx = findPeer(msg->srcMac);
    if (peerIdx < 0) {
        // Get RSSI (approximate)
        int8_t rssi = -50;  // Would need proper RSSI reading
        peerIdx = addPeer(msg->srcMac, rssi, msg->hopCount, msg->data[0] == 1);
    } else {
        peers[peerIdx].lastSeen = millis();
        peers[peerIdx].hopCount = msg->hopCount;
    }
    
    switch (msg->type) {
        case MSG_DISCOVERY:
            handleDiscovery(msg);
            break;
            
        case MSG_HEARTBEAT:
            // Already updated peer info above
            break;
            
        case MSG_DATA:
            handleData(msg);
            break;
            
        case MSG_ROUTE_REQUEST:
            handleRouteRequest(msg);
            break;
            
        case MSG_ROUTE_REPLY:
            handleRouteReply(msg);
            break;
    }
}

void handleDiscovery(MeshMessage* msg) {
    Serial.printf("[MESH] Discovery from %02X:%02X:%02X:%02X:%02X:%02X\n",
        msg->srcMac[0], msg->srcMac[1], msg->srcMac[2],
        msg->srcMac[3], msg->srcMac[4], msg->srcMac[5]);
    
    // Reply with our own discovery
    if (msg->hopCount < 3) {
        MeshMessage reply;
        reply.type = MSG_DISCOVERY;
        memcpy(reply.srcMac, myMac, 6);
        memcpy(reply.dstMac, msg->srcMac, 6);
        reply.hopCount = msg->hopCount + 1;
        reply.sequenceNum = sequenceNumber++;
        reply.dataLen = 1;
        reply.data[0] = isGateway ? 1 : 0;
        
        sendUnicast(msg->srcMac, &reply);
    }
    
    // Update routing table
    updateRoute(msg->srcMac, msg->srcMac, 1);
}

void handleData(MeshMessage* msg) {
    // Check if for us
    if (memcmp(msg->dstMac, myMac, 6) == 0) {
        // Deliver to application
        if (onDataReceived) {
            onDataReceived(msg->srcMac, msg->data, msg->dataLen);
        }
        return;
    }
    
    // Forward if hop count allows
    if (msg->hopCount < 5) {
        msg->hopCount++;
        
        RouteEntry* route = findRoute(msg->dstMac);
        if (route != nullptr) {
            sendUnicast(route->nextHop, msg);
        } else {
            // Broadcast if no route known
            sendBroadcast(msg);
        }
    }
}

void handleRouteRequest(MeshMessage* msg) {
    // Check if we know the destination
    RouteEntry* route = findRoute(msg->data);
    
    if (route != nullptr || memcmp(msg->data, myMac, 6) == 0) {
        // Send route reply
        MeshMessage reply;
        reply.type = MSG_ROUTE_REPLY;
        memcpy(reply.srcMac, myMac, 6);
        memcpy(reply.dstMac, msg->srcMac, 6);
        reply.hopCount = 0;
        reply.sequenceNum = sequenceNumber++;
        reply.dataLen = 7;
        memcpy(reply.data, msg->data, 6);  // Destination
        reply.data[6] = route ? route->hopCount + 1 : 1;
        
        sendUnicast(msg->srcMac, &reply);
    } else if (msg->hopCount < 5) {
        // Forward request
        msg->hopCount++;
        sendBroadcast(msg);
    }
}

void handleRouteReply(MeshMessage* msg) {
    // Update routing table
    uint8_t hopCount = msg->data[6];
    updateRoute(msg->data, msg->srcMac, hopCount);
}

// ==================== Peer Management ====================

int findPeer(uint8_t* mac) {
    for (int i = 0; i < peerCount; i++) {
        if (memcmp(peers[i].mac, mac, 6) == 0) {
            return i;
        }
    }
    return -1;
}

int addPeer(uint8_t* mac, int8_t rssi, uint8_t hopCount, bool isGatewayPeer) {
    if (peerCount >= MAX_PEERS) {
        removeStalePeers();
        if (peerCount >= MAX_PEERS) return -1;
    }
    
    int idx = peerCount++;
    memcpy(peers[idx].mac, mac, 6);
    peers[idx].rssi = rssi;
    peers[idx].lastSeen = millis();
    peers[idx].hopCount = hopCount;
    peers[idx].isGateway = isGatewayPeer;
    peers[idx].isActive = true;
    
    Serial.printf("[MESH] Added peer: %02X:%02X:%02X:%02X:%02X:%02X (gateway=%d)\n",
        mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], isGatewayPeer);
    
    return idx;
}

void removeStalePeers() {
    uint32_t now = millis();
    int writeIdx = 0;
    
    for (int i = 0; i < peerCount; i++) {
        if (now - peers[i].lastSeen < PEER_TIMEOUT) {
            if (writeIdx != i) {
                memcpy(&peers[writeIdx], &peers[i], sizeof(MeshPeer));
            }
            writeIdx++;
        } else {
            Serial.printf("[MESH] Removed stale peer: %02X:%02X\n",
                peers[i].mac[4], peers[i].mac[5]);
        }
    }
    
    peerCount = writeIdx;
}

// ==================== Routing Table ====================

RouteEntry* findRoute(uint8_t* dest) {
    for (int i = 0; i < routeCount; i++) {
        if (memcmp(routingTable[i].destination, dest, 6) == 0) {
            return &routingTable[i];
        }
    }
    return nullptr;
}

void updateRoute(uint8_t* dest, uint8_t* nextHop, uint8_t hopCount) {
    RouteEntry* existing = findRoute(dest);
    
    if (existing != nullptr) {
        // Update if better route
        if (hopCount < existing->hopCount) {
            memcpy(existing->nextHop, nextHop, 6);
            existing->hopCount = hopCount;
        }
        existing->lastUpdated = millis();
    } else {
        // Add new route
        if (routeCount < MAX_PEERS) {
            memcpy(routingTable[routeCount].destination, dest, 6);
            memcpy(routingTable[routeCount].nextHop, nextHop, 6);
            routingTable[routeCount].hopCount = hopCount;
            routingTable[routeCount].lastUpdated = millis();
            routeCount++;
        }
    }
}

// ==================== Main Loop Functions ====================

void meshLoop() {
    uint32_t now = millis();
    
    // Send periodic heartbeat
    if (now - lastHeartbeat > HEARTBEAT_INTERVAL) {
        sendHeartbeat();
        lastHeartbeat = now;
        
        // Remove stale peers periodically
        removeStalePeers();
    }
}

void setDataCallback(DataCallback callback) {
    onDataReceived = callback;
}

void setGatewayMode(bool gateway) {
    isGateway = gateway;
}

int getPeerCount() {
    return peerCount;
}

MeshPeer* getNearestGateway() {
    MeshPeer* nearest = nullptr;
    uint8_t minHops = 255;
    
    for (int i = 0; i < peerCount; i++) {
        if (peers[i].isGateway && peers[i].hopCount < minHops) {
            nearest = &peers[i];
            minHops = peers[i].hopCount;
        }
    }
    
    return nearest;
}
