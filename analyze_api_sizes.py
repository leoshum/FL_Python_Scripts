import json
import os
import re

def analyze_api_sizes():
    files = [
        "frontline-website-load-time-script/texas-automation-stg-acc.ss.frontlineeducation.com_1.txt",
        "frontline-website-load-time-script/texas-automation-stg-acc.ss.frontlineeducation.com_2.txt", 
        "frontline-website-load-time-script/texas-automation-stg-acc.ss.frontlineeducation.com_3.txt",
        "frontline-website-load-time-script/texas-automation-stg-acc.ss.frontlineeducation.com_4.txt"
    ]
    
    total_transfer_size = 0
    total_content_size = 0
    api_requests = []
    
    for file_path in files:
        print(f"\nAnalyzing {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content into request blocks
        request_blocks = content.split('"_connectionId"')
        
        for block in request_blocks:
            # Look for API URLs only
            api_match = re.search(r'"url": "(https://texas-automation-stg-acc\.ss\.frontlineeducation\.com/plan/api/[^"]*)"', block)
            
            if api_match:
                url = api_match.group(1)
                
                # Find all size types in the same block - use same logic as load-time-script.py
                transfer_match = re.search(r'"_transferSize": (\d+)', block)
                decoded_match = re.search(r'"_decodedBodySize": (\d+)', block)
                encoded_match = re.search(r'"_encodedBodySize": (\d+)', block)
                content_match = re.search(r'"size": (\d+)', block)
                
                transfer_size = int(transfer_match.group(1)) if transfer_match else 0
                decoded_size = int(decoded_match.group(1)) if decoded_match else 0
                encoded_size = int(encoded_match.group(1)) if encoded_match else 0
                content_size = int(content_match.group(1)) if content_match else 0
                
                # Use same priority logic as load-time-script.py
                if transfer_size and transfer_size > 0:
                    network_size = transfer_size
                elif decoded_size and decoded_size > 0:
                    network_size = decoded_size
                elif encoded_size and encoded_size > 0:
                    network_size = encoded_size
                else:
                    network_size = 0
                
                api_requests.append({
                    'url': url,
                    'network_size': network_size,
                    'transfer_size': transfer_size,
                    'decoded_size': decoded_size,
                    'encoded_size': encoded_size,
                    'content_size': content_size,
                    'file': file_path
                })
                
                total_transfer_size += network_size
                total_content_size += content_size
                
                print(f"  {url}")
                print(f"    Network: {network_size:,} bytes (T:{transfer_size} D:{decoded_size} E:{encoded_size})")
                print(f"    Content: {content_size:,} bytes")
    
    # Remove duplicates
    unique_requests = {}
    for req in api_requests:
        key = req['url']
        if key not in unique_requests:
            unique_requests[key] = req
        else:
            # Keep the one with larger network size
            if req['network_size'] > unique_requests[key]['network_size']:
                unique_requests[key] = req
    
    api_requests = list(unique_requests.values())
    
    # Recalculate totals
    total_transfer_size = sum(req['network_size'] for req in api_requests)
    total_content_size = sum(req['content_size'] for req in api_requests)
    
    # Summary
    print("\n" + "="*80)
    print("API DATA SIZE ANALYSIS SUMMARY")
    print("="*80)
    print(f"Total unique API requests: {len(api_requests)}")
    print(f"Total network size (using priority logic): {total_transfer_size:,} bytes ({total_transfer_size/1024:.1f} KB)")
    print(f"Total content size (decoded): {total_content_size:,} bytes ({total_content_size/1024:.1f} KB)")
    
    if total_transfer_size > 0:
        compression_ratio = (total_transfer_size / total_content_size) * 100
        print(f"Compression efficiency: {compression_ratio:.1f}% (network size vs decoded size)")
    
    # Top largest requests by network size
    print("\nTop 10 largest API requests (by network size):")
    sorted_requests = sorted(api_requests, key=lambda x: x['network_size'], reverse=True)
    for i, req in enumerate(sorted_requests[:10]):
        endpoint = req['url'].split('/plan/api/')[-1]
        print(f"{i+1:2d}. {req['network_size']:7,} bytes ({req['network_size']/1024:.1f} KB) - {endpoint}")
    
    # Top largest requests by content size
    print("\nTop 10 largest API requests (by content size):")
    sorted_by_content = sorted(api_requests, key=lambda x: x['content_size'], reverse=True)
    for i, req in enumerate(sorted_by_content[:10]):
        endpoint = req['url'].split('/plan/api/')[-1]
        print(f"{i+1:2d}. {req['content_size']:7,} bytes ({req['content_size']/1024:.1f} KB) - {endpoint}")
    
    return {
        'total_requests': len(api_requests),
        'total_network_size': total_transfer_size,
        'total_content_size': total_content_size,
        'requests': api_requests
    }

if __name__ == "__main__":
    result = analyze_api_sizes() 