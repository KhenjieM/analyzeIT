import urllib.request
import urllib.error
import urllib.parse
import queue
import threading
import time
import sys
import os
from urllib.parse import urljoin

class HiddenFolderCrawler:
    def __init__(self, base_url, wordlist=None, max_threads=10, delay=1, output_file=None):
        self.base_url = base_url if base_url.startswith('http') else f'http://{base_url}'
        self.wordlist = wordlist or self.default_wordlist()
        self.max_threads = max_threads
        self.delay = delay
        self.output_file = output_file
        self.queue = queue.Queue()
        self.found_dirs = []
        self.checked_urls = set()
        self.lock = threading.Lock()
        
    @staticmethod
    def default_wordlist():
        """Returns a basic wordlist of common directory names"""
        return [
            'admin', 'backup', 'bin', 'config', 'data', 'database', 'doc', 'docs',
            'download', 'ftp', 'files', 'images', 'img', 'include', 'inc', 'js',
            'lib', 'log', 'logs', 'media', 'old', 'secret', 'secure', 'src',
            'static', 'temp', 'test', 'tmp', 'upload', 'uploads', 'var', 'web'
        ]
    
    def check_url(self, url):
        """Check if a URL exists by making a HEAD request"""
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req) as response:
                return response.getcode()
        except urllib.error.HTTPError as e:
            return e.code
        except urllib.error.URLError:
            return None
    
    def worker(self):
        """Worker thread that processes URLs from the queue"""
        while True:
            path = self.queue.get()
            if path is None:  # Sentinel value to exit
                self.queue.task_done()
                break
                
            full_url = urljoin(self.base_url, path)
            
            # Skip if we've already checked this URL
            with self.lock:
                if full_url in self.checked_urls:
                    self.queue.task_done()
                    continue
                self.checked_urls.add(full_url)
            
            # Check the URL
            status = self.check_url(full_url)
            
            if status == 200:
                with self.lock:
                    self.found_dirs.append(full_url)
                print(f"[+] Found: {full_url} (Status: {status})")
            
            # Respect the delay between requests
            time.sleep(self.delay)
            self.queue.task_done()
    
    def save_results(self):
        """Save found directories to output file"""
        if not self.output_file:
            return
            
        try:
            with open(self.output_file, 'w') as f:
                f.write("Found directories:\n")
                f.write("\n".join(self.found_dirs))
            print(f"\n[+] Results saved to {self.output_file}")
        except IOError as e:
            print(f"\n[-] Error saving results: {e}")
    
    def crawl(self):
        """Start crawling with multiple threads"""
        print(f"[*] Starting crawl on {self.base_url}")
        print(f"[*] Using {self.max_threads} threads with {self.delay}s delay between requests")
        if self.output_file:
            print(f"[*] Results will be saved to {self.output_file}")
        
        # Add initial paths to queue
        for word in self.wordlist:
            self.queue.put(word)
            self.queue.put(f"{word}/")  # Try both with and without trailing slash
        
        # Start worker threads
        threads = []
        for _ in range(self.max_threads):
            t = threading.Thread(target=self.worker)
            t.start()
            threads.append(t)
        
        # Wait for queue to be empty
        self.queue.join()
        
        # Stop workers
        for _ in range(self.max_threads):
            self.queue.put(None)
        for t in threads:
            t.join()
        
        # Print summary
        print("\n[*] Crawl complete!")
        if self.found_dirs:
            print("[+] Found directories:")
            for url in self.found_dirs:
                print(f"  - {url}")
            
            # Save results if output file specified
            self.save_results()
        else:
            print("[-] No directories found")

def main():
    parser = argparse.ArgumentParser(
        description="Website Hidden Folder Crawler - by Khenjie Macalanda",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python analyze.py https://example.com
  python analyze.py https://example.com -w wordlist.txt -t 20 -d 0.5 -o results.txt
""")
    
    parser.add_argument("url", help="Base URL to scan (include http:// or https://)")
    parser.add_argument("-w", "--wordlist", 
                       help="Path to custom wordlist file (one entry per line)")
    parser.add_argument("-t", "--threads", type=int, default=10,
                       help="Number of threads to use (default: 10)")
    parser.add_argument("-d", "--delay", type=float, default=1.0,
                       help="Delay between requests in seconds (default: 1.0)")
    parser.add_argument("-o", "--output",
                       help="Output file to save results")
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Load custom wordlist if provided
    wordlist = None
    if args.wordlist:
        try:
            with open(args.wordlist, 'r') as f:
                wordlist = [line.strip() for line in f if line.strip()]
            print(f"[*] Loaded {len(wordlist)} entries from wordlist")
        except IOError:
            print(f"[-] Error: Could not read wordlist file {args.wordlist}")
            sys.exit(1)
    
    # Start crawling
    crawler = HiddenFolderCrawler(
        base_url=args.url,
        wordlist=wordlist,
        max_threads=args.threads,
        delay=args.delay,
        output_file=args.output
    )
    
    crawler.crawl()

if __name__ == "__main__":
    import argparse
    main()