# DoSEnv

A Python-based load testing tool for legitimate stress testing and performance evaluation of web applications.

## Features

- Concurrent request handling using asyncio
- Detailed statistics and metrics
- Response time tracking (min, max, average)
- Status code distribution
- Graceful shutdown handling
- Customizable HTTP methods and headers
- Request body support for POST/PUT requests
- Proxy support (HTTP/HTTPS with optional authentication)

## Installation

1. Install Python 3.7 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Example

Test a local server with 1000 requests and 50 concurrent connections:
```bash
python load_tester.py -u http://localhost:8000 -n 1000 -c 50
```

### Command Line Options

```
-u, --url           Target URL to test (required)
-n, --num-requests  Total number of requests (default: 100)
-c, --concurrency   Number of concurrent requests (default: 10)
-m, --method        HTTP method: GET, POST, PUT, DELETE, PATCH (default: GET)
-H, --header        Custom header (can be used multiple times, format: "Key: Value")
-d, --data          Request body data (for POST/PUT requests)
-p, --proxy         Proxy URL (e.g., http://proxy.example.com:8080 or http://user:pass@proxy.example.com:8080)
```

### Examples

**GET Request:**
```bash
python load_tester.py -u http://localhost:8000/api/users -n 500 -c 25
```

**POST Request with JSON:**
```bash
python load_tester.py -u http://localhost:8000/api/login -n 200 -c 10 \
  -m POST -d '{"username":"test","password":"test"}' \
  -H "Content-Type: application/json"
```

**With Authentication Header:**
```bash
python load_tester.py -u http://localhost:8000/api/protected -n 1000 -c 50 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**With Proxy:**
```bash
python load_tester.py -u http://example.com -n 1000 -c 50 \
  -p http://proxy.example.com:8080
```

**With Authenticated Proxy:**
```bash
python load_tester.py -u http://example.com -n 1000 -c 50 \
  -p http://username:password@proxy.example.com:8080
```

## Output

The tool provides detailed statistics including:

- Total requests sent
- Success/failure counts and percentages
- Requests per second
- Response time statistics (min, max, average)
- Status code distribution
- Test duration

Example output:
```
📈 Test Results
============================================================
Total Requests: 1000
Successful: 985 (98.50%)
Failed: 15 (1.50%)
Duration: 12.34 seconds
Requests/sec: 81.04

Response Times:
  Average: 615.23 ms
  Min: 120.45 ms
  Max: 2340.12 ms

Status Codes:
  200: 985
  500: 15
============================================================
```

## Best Practices

1. **Start Small**: Begin with low concurrency and request counts to understand your target's behavior
2. **Monitor Resources**: Watch CPU, memory, and network usage on both client and server
3. **Respect Rate Limits**: Be aware of rate limiting on the target server
4. **Test Gradually**: Increase load gradually to identify breaking points
5. **Use Proper Authorization**: Only test systems you own or have explicit permission to test

## Troubleshooting

- **Connection Errors**: Check if the target URL is accessible
- **Timeout Errors**: Increase timeout or reduce concurrency
- **High Failure Rate**: The server may be overloaded or rate-limiting requests

## License

This tool is provided for educational and legitimate testing purposes only. Use at your own risk and ensure you have proper authorization before testing any system. RONALDO!

## Disclaimer

The authors and contributors of this tool are not responsible for any misuse or illegal use of this software. Users are solely responsible for ensuring they have proper authorization before using this tool.