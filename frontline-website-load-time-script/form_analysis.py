#!/usr/bin/env python3
"""
Form Loading Analysis Tool
Captures loading indicators, network requests, and console errors
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from frontline_selenium.selenium_helper import SeleniumHelper

def setup_driver():
    """Setup Chrome driver for analysis"""
    options = Options()
    # options.add_argument("--headless=new")  # Comment out to see visual progress
    driver = webdriver.Chrome(options=options)
    return driver

def run_form_analysis(driver, url, duration=15):
    """Run form loading analysis"""
    print(f"Analyzing: {url}")
    print(f"Duration: {duration}s")
    
    try:
        driver.get(url)
        time.sleep(2)
        
        # Read and inject monitor script
        script_path = os.path.join(os.path.dirname(__file__), 'form_analysis.js')
        with open(script_path, 'r', encoding='utf-8') as f:
            monitor_script = f.read()
        
        driver.execute_script(monitor_script)
        driver.execute_script("window.formMonitor.start();")
        
        for i in range(duration):
            time.sleep(1)
            
            try:
                status = driver.execute_script("""
                    if (!window.formMonitor) return { requests: 0, errors: 0, loaders: 0 };
                    
                    return {
                        requests: window.formMonitor.networkRequests.length,
                        errors: window.formMonitor.consoleErrors.length,
                        loaders: window.formMonitor.getCurrentLoaders().length
                    };
                """)
                
                if i % 5 == 0:
                    print(f"{i+1}s: {status['requests']} requests, {status['errors']} errors, {status['loaders']} loaders")
                        
            except:
                pass
        
        results = driver.execute_script("""
            return window.formMonitor ? 
                   window.formMonitor.stop() : 
                   { error: 'Monitor not available' };
        """)
        
        return results
        
    except Exception as e:
        return {"error": str(e)}

def analyze_results(results, url):
    """Display analysis results"""
    print(f"\nRESULTS FOR: {url}")
    print("=" * 60)
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    duration = results.get('duration', 0) / 1000
    summary = results.get('summary', {})
    network_requests = results.get('networkRequests', [])
    console_errors = results.get('consoleErrors', [])
    final_loaders = results.get('finalLoaders', [])
    performance = results.get('performance', {})
    
    print(f"Duration: {duration:.1f}s")
    print(f"Network Requests: {summary.get('totalRequests', 0)}")
    print(f"Failed Requests: {summary.get('failedRequests', 0)}")
    print(f"Console Errors: {summary.get('totalErrors', 0)}")
    print(f"Loading Events: {summary.get('loadingEvents', 0)}")
    
    if final_loaders:
        print(f"\nStill Loading: {len(final_loaders)} indicators")
        for loader in final_loaders[:3]:
            print(f"  {loader.get('tag', 'unknown')} {loader.get('classes', '')[:40]}")
    
    if network_requests:
        print(f"\nNetwork Summary:")
        failed_requests = [r for r in network_requests if r.get('status', 0) >= 400]
        if failed_requests:
            print(f"Failed Requests ({len(failed_requests)}):")
            for req in failed_requests[:5]:
                print(f"  {req.get('status', 0)} {req.get('method', '')} {req.get('url', '')[:60]}")
        
        total_size = sum(r.get('responseSize', 0) for r in network_requests) / 1024
        avg_duration = sum(r.get('duration', 0) for r in network_requests) / len(network_requests) if network_requests else 0
        print(f"Total Response Size: {total_size:.1f}KB")
        print(f"Average Request Duration: {avg_duration:.0f}ms")
    
    if console_errors:
        print(f"\nConsole Errors ({len(console_errors)}):")
        for error in console_errors[:3]:
            print(f"  {error.get('type', 'unknown')}: {error.get('message', '')[:80]}")
    
    if performance and isinstance(performance, dict):
        print(f"\nPerformance:")
        dom_interactive = performance.get('domInteractive', 0)
        dom_content_loaded = performance.get('domContentLoaded', 0)
        load_complete = performance.get('loadComplete', 0)
        
        if dom_interactive is not None:
            print(f"  DOM Interactive: {dom_interactive:.0f}ms")
        if dom_content_loaded is not None:
            print(f"  DOM Content Loaded: {dom_content_loaded:.0f}ms")
        if load_complete is not None:
            print(f"  Load Complete: {load_complete:.0f}ms")

def save_results(results, url):
    """Save results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    domain = url.split('/')[2] if '/' in url else 'unknown'
    filename = f"form_analysis_{domain}_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'url': url,
            'timestamp': timestamp,
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {filename}")
    return filename

def main():
    parser = argparse.ArgumentParser(description='Analyze form loading performance')
    parser.add_argument('url', help='Form URL to analyze')
    parser.add_argument('--duration', type=int, default=15, help='Monitoring duration in seconds (default: 15)')
    
    args = parser.parse_args()
    
    driver = setup_driver()
    
    try:
        base_url = '/'.join(args.url.split('/')[:3])
        SeleniumHelper.login_user(base_url, driver, "SFTDVTester", "ht2jGMM2GnC3bwX7")        
        results = run_form_analysis(driver, args.url, args.duration)        
        analyze_results(results, args.url)        
        save_results(results, args.url)       
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main() 