#!/usr/bin/env python3
"""
Simple database connection test script
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_connection():
    """Test database connection with different methods"""
    database_url = os.getenv('DATABASE_URL')
    print(f"Testing connection to: {database_url}")
    
    # Method 1: Direct IPv4 connection
    try:
        print("\n=== Testing IPv4 Direct Connection ===")
        pool = await asyncio.wait_for(
            asyncpg.create_pool(
                host='104.18.38.10',
                port=5432,
                user='postgres',
                password='SParshitha06',
                database='postgres',
                ssl='require',
                min_size=1,
                max_size=2,
                command_timeout=10
            ),
            timeout=15.0
        )
        
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            print(f"✅ IPv4 connection successful! Result: {result}")
        
        await pool.close()
        return True
        
    except Exception as e:
        print(f"❌ IPv4 connection failed: {e}")
    
    # Method 2: Original URL
    try:
        print("\n=== Testing Original URL ===")
        pool = await asyncio.wait_for(
            asyncpg.create_pool(database_url, min_size=1, max_size=2),
            timeout=15.0
        )
        
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            print(f"✅ Original URL connection successful! Result: {result}")
        
        await pool.close()
        return True
        
    except Exception as e:
        print(f"❌ Original URL connection failed: {e}")
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        print("\n🎉 Database connection test PASSED!")
    else:
        print("\n💥 Database connection test FAILED!")