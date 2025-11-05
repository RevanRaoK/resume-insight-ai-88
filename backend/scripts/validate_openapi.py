#!/usr/bin/env python3
"""
OpenAPI specification validation script
"""
import json
import yaml
import sys
from pathlib import Path

def validate_openapi_spec():
    """Validate the OpenAPI specification file"""
    
    # Path to OpenAPI spec
    spec_path = Path(__file__).parent.parent / "docs" / "openapi.yaml"
    
    if not spec_path.exists():
        print(f"ERROR: OpenAPI spec not found at {spec_path}")
        return False
    
    try:
        # Load and parse YAML
        with open(spec_path, 'r') as f:
            spec = yaml.safe_load(f)
        
        print("✓ OpenAPI YAML syntax is valid")
        
        # Basic structure validation
        required_fields = ['openapi', 'info', 'paths']
        for field in required_fields:
            if field not in spec:
                print(f"ERROR: Missing required field '{field}'")
                return False
        
        print("✓ Required top-level fields present")
        
        # Validate OpenAPI version
        if not spec['openapi'].startswith('3.'):
            print(f"WARNING: OpenAPI version {spec['openapi']} may not be supported")
        else:
            print(f"✓ OpenAPI version {spec['openapi']} is valid")
        
        # Validate info section
        info_required = ['title', 'version']
        for field in info_required:
            if field not in spec['info']:
                print(f"ERROR: Missing required info field '{field}'")
                return False
        
        print("✓ Info section is valid")
        
        # Count paths and operations
        path_count = len(spec['paths'])
        operation_count = 0
        
        for path, methods in spec['paths'].items():
            for method in methods:
                if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    operation_count += 1
        
        print(f"✓ Found {path_count} paths with {operation_count} operations")
        
        # Validate components section
        if 'components' in spec:
            if 'schemas' in spec['components']:
                schema_count = len(spec['components']['schemas'])
                print(f"✓ Found {schema_count} schema definitions")
            
            if 'securitySchemes' in spec['components']:
                security_count = len(spec['components']['securitySchemes'])
                print(f"✓ Found {security_count} security schemes")
        
        # Check for examples
        example_count = 0
        for path, methods in spec['paths'].items():
            for method, operation in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    if 'responses' in operation:
                        for status, response in operation['responses'].items():
                            if 'content' in response:
                                for media_type, content in response['content'].items():
                                    if 'example' in content or 'examples' in content:
                                        example_count += 1
        
        print(f"✓ Found {example_count} response examples")
        
        print("\n🎉 OpenAPI specification validation passed!")
        return True
        
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML syntax: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Validation failed: {e}")
        return False

def generate_api_summary():
    """Generate a summary of the API specification"""
    
    spec_path = Path(__file__).parent.parent / "docs" / "openapi.yaml"
    
    try:
        with open(spec_path, 'r') as f:
            spec = yaml.safe_load(f)
        
        print("\n" + "="*50)
        print("API SPECIFICATION SUMMARY")
        print("="*50)
        
        # Basic info
        print(f"Title: {spec['info']['title']}")
        print(f"Version: {spec['info']['version']}")
        print(f"Description: {spec['info'].get('description', 'N/A')[:100]}...")
        
        # Servers
        if 'servers' in spec:
            print(f"\nServers:")
            for server in spec['servers']:
                print(f"  - {server['url']} ({server.get('description', 'No description')})")
        
        # Tags
        if 'tags' in spec:
            print(f"\nTags:")
            for tag in spec['tags']:
                print(f"  - {tag['name']}: {tag.get('description', 'No description')}")
        
        # Paths by tag
        print(f"\nEndpoints by Tag:")
        
        # Group paths by tag
        paths_by_tag = {}
        for path, methods in spec['paths'].items():
            for method, operation in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    tags = operation.get('tags', ['untagged'])
                    for tag in tags:
                        if tag not in paths_by_tag:
                            paths_by_tag[tag] = []
                        paths_by_tag[tag].append(f"{method.upper()} {path}")
        
        for tag, endpoints in paths_by_tag.items():
            print(f"\n  {tag.title()}:")
            for endpoint in endpoints:
                print(f"    - {endpoint}")
        
        # Security
        if 'security' in spec:
            print(f"\nSecurity:")
            for security_req in spec['security']:
                for scheme, scopes in security_req.items():
                    print(f"  - {scheme}: {scopes}")
        
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"ERROR: Could not generate summary: {e}")

if __name__ == "__main__":
    success = validate_openapi_spec()
    
    if success:
        generate_api_summary()
        sys.exit(0)
    else:
        sys.exit(1)