#!/usr/bin/env python3
"""
dosenv Tool
=================

⚠️  WARNING: This tool is for LEGITIMATE purposes only:
- Load testing your own applications
- Stress testing services you own or have explicit permission to test
- Educational purposes with proper authorization

Using this tool to attack systems without authorization is ILLEGAL
and may result in criminal prosecution.

Authorized use only - Use responsibly!
"""

import asyncio
import aiohttp
import time
import argparse
import sys
from typing import List, Dict
import signal


class LoadTester:
    def __init__(self, url: str, num_requests: int, concurrency: int, 
                 method: str = 'GET', headers: Dict = None, data: str = None,
                 proxy: str = None):
        """
        Initialize the load tester.
        
        Args:
            url: Target URL to test
            num_requests: Total number of requests to send
            concurrency: Number of concurrent requests
            method: HTTP method (GET, POST, etc.)
            headers: Optional custom headers
            data: Optional request body data
            proxy: Optional proxy URL (e.g., http://proxy.example.com:8080)
        """
        self.url = url
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.method = method.upper()
        self.headers = headers or {}
        self.data = data
        self.proxy = proxy
        
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'status_codes': {},
            'errors': {},  # Track error details
            'response_times': [],
            'start_time': None,
            'end_time': None
        }
        self.running = True
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        print("\n\n⚠️  Interrupt received. Stopping load test...")
        self.running = False
    
    async def _make_request(self, session: aiohttp.ClientSession, request_id: int, retry_count: int = 0) -> Dict:
        """Make a single HTTP request with retry logic for connection errors."""
        if not self.running:
            return None
        
        start_time = time.time()
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms delay
        
        try:
            async with session.request(
                self.method,
                self.url,
                headers=self.headers,
                data=self.data,
                proxy=self.proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = time.time() - start_time
                await response.read()  # Read response body
                
                status_code = response.status
                return {
                    'request_id': request_id,
                    'status_code': status_code,
                    'response_time': response_time,
                    'success': 200 <= status_code < 400
                }
        except asyncio.TimeoutError:
            # Retry timeout errors
            if retry_count < max_retries:
                await asyncio.sleep(retry_delay * (2 ** retry_count))
                return await self._make_request(session, request_id, retry_count + 1)
            error_type = 'TimeoutError'
            error_msg = 'Request timed out after 30 seconds'
            return {
                'request_id': request_id,
                'status_code': 'TIMEOUT',
                'response_time': time.time() - start_time,
                'success': False,
                'error_type': error_type,
                'error': error_msg
            }
        except (aiohttp.ClientConnectorError, aiohttp.ServerConnectionError, ConnectionError) as e:
            # Retry connection errors with exponential backoff
            if retry_count < max_retries:
                await asyncio.sleep(retry_delay * (2 ** retry_count))
                return await self._make_request(session, request_id, retry_count + 1)
            error_type = type(e).__name__
            error_msg = str(e)
            return {
                'request_id': request_id,
                'status_code': 'CONNECTION_ERROR',
                'response_time': time.time() - start_time,
                'success': False,
                'error_type': error_type,
                'error': error_msg
            }
        except aiohttp.ClientProxyConnectionError as e:
            # Retry proxy connection errors
            if retry_count < max_retries:
                await asyncio.sleep(retry_delay * (2 ** retry_count))
                return await self._make_request(session, request_id, retry_count + 1)
            error_type = 'ClientProxyConnectionError'
            error_msg = str(e)
            return {
                'request_id': request_id,
                'status_code': 'PROXY_ERROR',
                'response_time': time.time() - start_time,
                'success': False,
                'error_type': error_type,
                'error': error_msg
            }
        except aiohttp.ClientResponseError as e:
            error_type = 'ClientResponseError'
            error_msg = f"HTTP {e.status}: {e.message}"
            return {
                'request_id': request_id,
                'status_code': e.status,
                'response_time': time.time() - start_time,
                'success': False,
                'error_type': error_type,
                'error': error_msg
            }
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            return {
                'request_id': request_id,
                'status_code': 'ERROR',
                'response_time': time.time() - start_time,
                'success': False,
                'error_type': error_type,
                'error': error_msg
            }
    
    async def _worker(self, session: aiohttp.ClientSession, queue: asyncio.Queue, worker_id: int = 0):
        """Worker coroutine that processes requests from the queue."""
        # Stagger worker startup to avoid connection storms
        if worker_id > 0:
            await asyncio.sleep(worker_id * 0.01)  # 10ms delay between workers
        
        while self.running:
            try:
                request_id = await asyncio.wait_for(queue.get(), timeout=0.1)
                result = await self._make_request(session, request_id)
                
                if result:
                    self._update_stats(result)
                
                queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
                break
    
    def _update_stats(self, result: Dict):
        """Update statistics with request result."""
        self.stats['total_requests'] += 1
        
        status = str(result['status_code'])
        if result['success']:
            self.stats['successful'] += 1
        else:
            self.stats['failed'] += 1
            # Track error details
            if 'error_type' in result:
                error_key = f"{result.get('error_type', 'Unknown')}: {result.get('error', 'No details')}"
                self.stats['errors'][error_key] = self.stats['errors'].get(error_key, 0) + 1
        
        self.stats['status_codes'][status] = self.stats['status_codes'].get(status, 0) + 1
        self.stats['response_times'].append(result['response_time'])
        
        # Print progress every 10 requests
        if self.stats['total_requests'] % 10 == 0:
            print(f"\r📊 Progress: {self.stats['total_requests']}/{self.num_requests} requests | "
                  f"Success: {self.stats['successful']} | Failed: {self.stats['failed']}", 
                  end='', flush=True)
    
    async def run(self):
        """Run the load test."""
        print("=" * 60)
        print("🚀 Starting Load Test")
        print("=" * 60)
        print(f"Target URL: {self.url}")
        print(f"Method: {self.method}")
        print(f"Total Requests: {self.num_requests}")
        print(f"Concurrency: {self.concurrency}")
        if self.proxy:
            print(f"Proxy: {self.proxy}")
        print("=" * 60)
        print()
        
        self.stats['start_time'] = time.time()
        
        # Create aiohttp session with proper connection pooling
        # Increase limit to allow more concurrent connections
        # Use limit_per_host to allow multiple connections per host
        connector = aiohttp.TCPConnector(
            limit=self.concurrency * 2,  # Allow more total connections
            limit_per_host=self.concurrency,  # Allow multiple connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            force_close=False,  # Reuse connections
            enable_cleanup_closed=True  # Clean up closed connections
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:
            # Warm up connections with a small batch first
            # This helps establish connections before the main load
            warmup_count = min(10, self.concurrency // 10, 50)
            if warmup_count > 0:
                print(f"🔥 Warming up connections ({warmup_count} requests)...")
                warmup_tasks = [
                    self._make_request(session, i)
                    for i in range(warmup_count)
                ]
                await asyncio.gather(*warmup_tasks, return_exceptions=True)
                # Reset stats after warmup (warmup requests don't count)
                self.stats['total_requests'] = 0
                self.stats['successful'] = 0
                self.stats['failed'] = 0
                self.stats['status_codes'] = {}
                self.stats['errors'] = {}
                self.stats['response_times'] = []
                print("✅ Warmup complete. Starting main load test...\n")
            
            # Create queue and workers with staggered startup
            queue = asyncio.Queue(maxsize=self.concurrency * 2)
            workers = [
                asyncio.create_task(self._worker(session, queue, worker_id=i))
                for i in range(self.concurrency)
            ]
            
            # Add requests to queue
            for i in range(self.num_requests):
                if not self.running:
                    break
                await queue.put(i + 1)
            
            # Wait for all requests to complete
            await queue.join()
            
            # Cancel workers
            for worker in workers:
                worker.cancel()
            
            await asyncio.gather(*workers, return_exceptions=True)
        
        self.stats['end_time'] = time.time()
        self._print_results()
    
    def _print_results(self):
        """Print test results and statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print("\n\n" + "=" * 60)
        print("📈 Test Results")
        print("=" * 60)
        print(f"Total Requests: {self.stats['total_requests']}")
        print(f"Successful: {self.stats['successful']} ({self.stats['successful']/max(self.stats['total_requests'], 1)*100:.2f}%)")
        print(f"Failed: {self.stats['failed']} ({self.stats['failed']/max(self.stats['total_requests'], 1)*100:.2f}%)")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Requests/sec: {self.stats['total_requests']/max(duration, 0.1):.2f}")
        
        if self.stats['response_times']:
            avg_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
            min_time = min(self.stats['response_times'])
            max_time = max(self.stats['response_times'])
            print(f"\nResponse Times:")
            print(f"  Average: {avg_time*1000:.2f} ms")
            print(f"  Min: {min_time*1000:.2f} ms")
            print(f"  Max: {max_time*1000:.2f} ms")
        
        print(f"\nStatus Codes:")
        for status, count in sorted(self.stats['status_codes'].items()):
            print(f"  {status}: {count}")
        
        # Display detailed error information
        if self.stats['errors']:
            print(f"\nError Details:")
            for error, count in sorted(self.stats['errors'].items(), key=lambda x: x[1], reverse=True):
                # Truncate long error messages for display
                error_display = error[:100] + "..." if len(error) > 100 else error
                print(f"  {error_display}: {count}")
        
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Load Testing Tool - For authorized testing only!',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  LEGAL WARNING:
This tool is for legitimate load testing purposes only. Using this tool
to attack systems without explicit authorization is ILLEGAL and may
result in criminal prosecution. Use responsibly and ethically.

Examples:
  # Basic load test
  python load_tester.py -u http://localhost:8000 -n 1000 -c 50
  
  # POST request with data
  python load_tester.py -u http://localhost:8000/api -n 500 -c 25 -m POST -d '{"key":"value"}'
  
  # With proxy
  python load_tester.py -u http://example.com -n 1000 -c 50 -p http://proxy.example.com:8080
  
  # With authenticated proxy
  python load_tester.py -u http://example.com -n 1000 -c 50 -p http://user:pass@proxy.example.com:8080
        """
    )
    
    parser.add_argument('-u', '--url', required=True,
                       help='Target URL to test')
    parser.add_argument('-n', '--num-requests', type=int, default=100,
                       help='Total number of requests (default: 100)')
    parser.add_argument('-c', '--concurrency', type=int, default=10,
                       help='Number of concurrent requests (default: 10)')
    parser.add_argument('-m', '--method', default='GET',
                       choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
                       help='HTTP method (default: GET)')
    parser.add_argument('-H', '--header', action='append',
                       help='Custom header (can be used multiple times, format: "Key: Value")')
    parser.add_argument('-d', '--data', type=str,
                       help='Request body data (for POST/PUT requests)')
    parser.add_argument('-p', '--proxy', type=str,
                       help='Proxy URL (e.g., http://proxy.example.com:8080 or http://user:pass@proxy.example.com:8080)')
    
    args = parser.parse_args()
    
    # Parse headers
    headers = {}
    if args.header:
        for header in args.header:
            if ':' in header:
                key, value = header.split(':', 1)
                headers[key.strip()] = value.strip()
    
    # Safety check: warn if large number of requests
    if args.num_requests > 10000:
        print("⚠️  WARNING: Large number of requests specified!")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    # Create and run tester
    tester = LoadTester(
        url=args.url,
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        method=args.method,
        headers=headers,
        data=args.data,
        proxy=args.proxy
    )
    
    try:
        asyncio.run(tester.run())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(0)


if __name__ == '__main__':
    main()

