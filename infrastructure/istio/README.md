# Istio Installation and Configuration

## Step 1: Install Istio CLI
Download and install the Istio CLI by following the official documentation:
https://istio.io/latest/docs/setup/getting-started/#download

## Step 2: Install Istio in Kubernetes
Run the following commands to install Istio:

```bash
istioctl install --set profile=demo -y
```

This installs Istio with the demo profile, which is suitable for development and testing.

## Step 3: Label the Namespace for Istio Injection
Enable automatic sidecar injection for your application's namespace:

```bash
kubectl label namespace <your-namespace> istio-injection=enabled
```

Replace `<your-namespace>` with the namespace where your application is deployed.

## Step 4: Configure Ingress Gateway
Create an `IngressGateway` resource to expose your services:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: app-gateway
spec:
  selector:
    istio: ingressgateway # Use Istio's default ingress gateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
```

## Step 5: Define VirtualService for Traffic Routing
Create a `VirtualService` to route traffic to your services:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: app-virtualservice
spec:
  hosts:
  - "*"
  gateways:
  - app-gateway
  http:
  - route:
    - destination:
        host: <your-service-name>
        port:
          number: 80
```

Replace `<your-service-name>` with the name of your service.

## Step 6: Enable mTLS
Secure service-to-service communication by enabling mTLS:

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

## Step 7: Integrate Istio Telemetry with Prometheus/Grafana
Istio comes with built-in telemetry. Ensure that your Prometheus and Grafana setups are configured to scrape Istio metrics.

## Step 8: Test the Setup
Verify that Istio is working correctly by accessing your services through the ingress gateway and checking the telemetry dashboards.
