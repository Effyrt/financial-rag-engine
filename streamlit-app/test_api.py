import requests
import json

# Your deployed FastAPI URL
API_URL = "https://financial-rag-api-387661610307.us-central1.run.app"

def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Testing Health Endpoint...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✅ Health check passed!\n")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}\n")
        return False

def test_query(concept):
    """Test query endpoint"""
    print("=" * 60)
    print(f"Testing Query: {concept}")
    print("=" * 60)
    
    try:
        # Try POST first (correct method)
        response = requests.post(
            f"{API_URL}/query",
            json={"concept": concept},
            timeout=60
        )
        
        # If POST fails with 405, try GET
        if response.status_code == 405:
            print("⚠️  POST not allowed, trying GET method...")
            response = requests.get(
                f"{API_URL}/query",
                params={"concept": concept},
                timeout=60
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 Response Structure:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Check required fields
            print(f"\n🔍 Field Check:")
            required_fields = ['concept', 'definition', 'source']
            for field in required_fields:
                if field in data:
                    print(f"  ✅ {field}: Present")
                else:
                    print(f"  ❌ {field}: Missing")
            
            print(f"\n✅ Query successful!")
            return data
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>60s). API might be cold starting.")
        print("   Try running the test again.")
        return None
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return None

def discover_endpoints():
    """Try to discover available endpoints"""
    print("=" * 60)
    print("Discovering Available Endpoints...")
    print("=" * 60)
    
    endpoints_to_try = [
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("POST", "/query"),
        ("GET", "/query"),
        ("POST", "/api/query"),
        ("GET", "/api/query"),
        ("POST", "/seed"),
        ("POST", "/api/seed"),
    ]
    
    available = []
    
    for method, path in endpoints_to_try:
        try:
            url = f"{API_URL}{path}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, json={}, timeout=5)
            
            if response.status_code not in [404, 405]:
                status = "✅" if response.status_code == 200 else f"⚠️  ({response.status_code})"
                print(f"{status} {method:6} {path}")
                available.append((method, path, response.status_code))
            
        except Exception as e:
            pass
    
    print(f"\nFound {len(available)} available endpoints")
    print(f"\n💡 Visit {API_URL}/docs for full API documentation\n")
    return available

def test_seed():
    """Test seed endpoint (if available)"""
    print("=" * 60)
    print("Testing Seed Endpoint...")
    print("=" * 60)
    
    try:
        # Try POST with concepts
        response = requests.post(
            f"{API_URL}/seed",
            json={"concepts": ["Credit Default Swap", "Value at Risk"]},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            print("✅ Seed endpoint working!")
        else:
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️  Seed endpoint timed out (not responding)")
    except Exception as e:
        print(f"ℹ️  Seed endpoint: {type(e).__name__}")

if __name__ == "__main__":
    print("\n🚀 Starting API Tests...\n")
    
    # Test 1: Health Check
    if not test_health():
        print("⚠️  API is not healthy. Stopping tests.")
        exit(1)
    
    # Discover endpoints
    print("\n")
    available = discover_endpoints()
    
    # Test 2: Query with textbook concept
    print("\n" + "=" * 60)
    print("TEST 1: Textbook Concept")
    test_query("Credit Default Swap")
    
    # Test 3: Query with non-textbook concept (should trigger Wikipedia)
    print("\n" + "=" * 60)
    print("TEST 2: Non-Textbook Concept (Wikipedia Fallback)")
    test_query("Quantum Computing")
    
    # Test 4: Seed endpoint (with timeout protection)
    print("\n")
    try:
        test_seed()
    except KeyboardInterrupt:
        print("\n⚠️  Seed test interrupted (likely not implemented)")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)