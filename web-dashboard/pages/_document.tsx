import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* PWA Meta Tags */}
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#667eea" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="IoT Network" />
        
        {/* Favicon */}
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
        
        {/* Fonts */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" 
          rel="stylesheet" 
        />
        
        {/* SEO Meta Tags */}
        <meta name="description" content="Decentralized IoT network sharing platform with blockchain rewards" />
        <meta name="keywords" content="IoT, blockchain, decentralized, network, rewards, cryptocurrency" />
        <meta name="author" content="IoT Network Team" />
        
        {/* Open Graph */}
        <meta property="og:title" content="Decentralized IoT Network" />
        <meta property="og:description" content="Share your network, earn rewards" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://iot-network.example.com" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
