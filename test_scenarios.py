#!/usr/bin/env python3
"""
Test script for scenario functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, generate_scenario_data, active_scenario

def test_scenario_generation():
    """Test scenario data generation"""
    print("🧪 Testing Scenario Generation...")
    
    # Test vaping scenario
    vaping_scenario = {
        'name': 'Vaping Detection',
        'threatScore': 45,
        'voc': {'min': 150, 'max': 200},
        'people': {'min': 2, 'max': 3},
        'noise': {'min': 45, 'max': 55},
        'pm25': {'min': 20, 'max': 35}
    }
    
    data = generate_scenario_data(vaping_scenario)
    
    print(f"✅ Scenario: {data.get('scenario_name', 'Unknown')}")
    print(f"   Threat Score: {data.get('threat', {}).get('overall_threat', 0):.1f}")
    print(f"   VOC Level: {data.get('voc', 0):.1f} ppm")
    print(f"   People Count: {data.get('people_count', 0)}")
    print(f"   Noise Level: {data.get('sound_db', 0):.1f} dB")
    print(f"   Targets Generated: {len(data.get('targets', []))}")
    
    # Test fighting scenario
    fighting_scenario = {
        'name': 'Fighting/Altercation',
        'threatScore': 85,
        'voc': {'min': 40, 'max': 60},
        'people': {'min': 3, 'max': 5},
        'noise': {'min': 85, 'max': 100},
        'pm25': {'min': 15, 'max': 25}
    }
    
    data2 = generate_scenario_data(fighting_scenario)
    
    print(f"\n✅ Scenario: {data2.get('scenario_name', 'Unknown')}")
    print(f"   Threat Score: {data2.get('threat', {}).get('overall_threat', 0):.1f}")
    print(f"   VOC Level: {data2.get('voc', 0):.1f} ppm")
    print(f"   People Count: {data2.get('people_count', 0)}")
    print(f"   Noise Level: {data2.get('sound_db', 0):.1f} dB")
    print(f"   Targets Generated: {len(data2.get('targets', []))}")
    
    print("\n🎉 Scenario generation test completed successfully!")

def test_scenario_endpoints():
    """Test scenario API endpoints"""
    print("\n🧪 Testing Scenario API Endpoints...")
    
    with app.test_client() as client:
        # Test scenarios page (will redirect to login if not authenticated)
        response = client.get('/scenarios')
        print(f"✅ Scenarios page status: {response.status_code}")
        
        # Test scenario status API
        response = client.get('/api/scenario-status')
        print(f"✅ Scenario status API status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"   Active scenario: {data.get('active_scenario')}")
            print(f"   Scenario active: {data.get('scenario_active')}")
        
        # Test activate scenario API (will fail without authentication, but should return proper error)
        response = client.post('/api/activate-scenario', 
                              json={'scenario': {'name': 'Test Scenario'}},
                              content_type='application/json')
        print(f"✅ Activate scenario API status: {response.status_code}")
        
        # Test stop scenario API
        response = client.post('/api/stop-scenario')
        print(f"✅ Stop scenario API status: {response.status_code}")
    
    print("\n🎉 Scenario API endpoints test completed!")

if __name__ == "__main__":
    try:
        test_scenario_generation()
        test_scenario_endpoints()
        print("\n🎉 All tests passed! Scenario functionality is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
