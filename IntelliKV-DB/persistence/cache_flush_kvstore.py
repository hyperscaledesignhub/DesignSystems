from persistence.commit_log import commit_log_write, commit_log_read
from persistence.cache import cache_put, cache_get, cache_keys, cache_clear
from persistence.sstable import sstable_write, sstable_read
import time
import glob
import os

class CacheMissError(Exception):
    """Raised when key is not found in cache"""
    pass

def flush_cache_to_sstable(namespace: str = "default") -> bool:
    """
    Flush all cache data to SSTable and clear cache.
    
    Args:
        namespace (str): The namespace for the cache and SSTables
        
    Returns:
        bool: True if flush was successful, False otherwise
    """
    try:
        # Step 1: Get all keys from cache
        keys = cache_keys(namespace=namespace)
        if not keys:
            return True  # Nothing to flush
        
        # Step 2: Generate unique SSTable filename
        timestamp = int(time.time() * 1000)  # Use milliseconds for better uniqueness
        sstable_filename = f"{namespace}/sstable_{timestamp}.data"
        
        # Create namespace directory if it doesn't exist
        os.makedirs(os.path.dirname(sstable_filename), exist_ok=True)
        
        # Step 3: Write all cache data to SSTable
        for key in keys:
            value = cache_get(key, namespace=namespace)
            if value is not None:
                sstable_write(key, value, sstable_filename)
        
        # Step 4: Clear the cache
        cache_clear(namespace=namespace)
        
        print(f"Flushed {len(keys)} entries to {sstable_filename}")
        return True
        
    except Exception as e:
        print(f"Flush failed: {e}")
        return False

def put(key: str, value: str, namespace: str = "default", max_size: int = 1000) -> bool:
    """
    Store key-value pair with cache flush when cache is full.
    
    Args:
        key (str): The key to store
        value (str): The value to store
        namespace (str): The namespace for storage
        max_size (int): Maximum cache size for this put operation
        
    Returns:
        bool: True if successful (commit log write succeeded), False otherwise
    """
    # Step 1: Write to commit log first (durability)
    try:
        commit_log_file = f"{namespace}/kvstore.log"
        os.makedirs(os.path.dirname(commit_log_file), exist_ok=True)
        commit_success = commit_log_write(key, value, commit_log_file)
        if not commit_success:
            return False
    except Exception:
        return False
    
    # Step 2: Try to write to cache
    try:
        cache_put(key, value, max_size=max_size, namespace=namespace)
        return True
    except Exception as e:
        # Check if cache is full
        if "memory is full" in str(e):
            # Step 3: Flush cache to SSTable
            flush_success = flush_cache_to_sstable(namespace=namespace)
            if not flush_success:
                print("Warning: Cache flush failed")
                return True  # Commit log succeeded, so operation succeeds
            
            # Step 4: Try cache write again (cache is now empty)
            try:
                cache_put(key, value, max_size=max_size, namespace=namespace)
            except Exception:
                print("Warning: Cache write failed after flush")
                # Still return True because commit log succeeded
        return True

def scan_sstables(key: str, namespace: str = "default") -> str:
    """
    Scan all SSTable files to find key, returns latest value or None.
    
    Args:
        key (str): The key to look up
        namespace (str): The namespace for SSTables
        
    Returns:
        str: The latest value for the key from SSTables, or None if not found
    """
    try:
        # Get all SSTable files in namespace directory
        sstable_pattern = f"{namespace}/sstable_*.data"
        sstable_files = glob.glob(sstable_pattern)
        if not sstable_files:
            return None
        
        # Sort by filename to process in chronological order
        # (later files have more recent data)
        sstable_files.sort()
        
        latest_value = None
        
        # Scan each SSTable file
        for sstable_file in sstable_files:
            value = sstable_read(key, sstable_file)
            if value is not None:
                latest_value = value  # Latest file wins
        
        return latest_value
        
    except Exception:
        return None

def get(key: str, namespace: str = "default") -> str:
    """
    Retrieve value for key from cache first, then SSTable fallback.
    
    Args:
        key (str): The key to look up
        namespace (str): The namespace for storage
        
    Returns:
        str: The value for the key, or None if not found in cache or SSTables
    """
    try:
        # Step 1: Check cache first (FAST PATH)
        cached_value = cache_get(key, namespace=namespace)
        if cached_value is not None:
            return cached_value
        
        # Step 2: Cache miss - scan SSTables (FALLBACK PATH)
        return scan_sstables(key, namespace=namespace)
        
    except Exception:
        return None

def verify_in_cache(key: str, expected_value: str, namespace: str = "default") -> bool:
    """
    Helper to verify key-value exists in cache.
    
    Args:
        key (str): The key to check
        expected_value (str): The expected value
        namespace (str): The namespace for the cache
        
    Returns:
        bool: True if key exists in cache with expected value
    """
    return cache_get(key, namespace=namespace) == expected_value

def verify_in_commit_log(key: str, expected_value: str, namespace: str = "default") -> bool:
    """
    Helper to verify key-value exists in commit log.
    
    Args:
        key (str): The key to check
        expected_value (str): The expected value
        namespace (str): The namespace for the commit log
        
    Returns:
        bool: True if key exists in commit log with expected value
    """
    commit_log_file = f"{namespace}/kvstore.log"
    return commit_log_read(key, commit_log_file) == expected_value

if __name__ == "__main__":
    # Example usage
    # Clear cache first
    cache_clear()
    
    # Store data (goes to commit log and cache)
    put("name", "Alice")
    put("age", "25")
    put("name", "Bob")  # Update in both
    
    # Fill cache to trigger flush
    for i in range(1000):
        put(f"key_{i}", f"value_{i}")
    
    # Next put should trigger cache flush
    put("extra_key", "extra_value")
    
    # Retrieve data (reads from commit log)
    print(f"Name: {get('name')}")  # Should print "Bob"
    print(f"Age: {get('age')}")    # Should print "25"
    print(f"City: {get('city')}")  # Should print "None"
    
    # Verify in both backends
    print(f"\nVerifying in cache:")
    print(f"Name in cache: {verify_in_cache('name', 'Bob')}")
    print(f"Age in cache: {verify_in_cache('age', '25')}")
    
    print(f"\nVerifying in commit log:")
    print(f"Name in commit log: {verify_in_commit_log('name', 'Bob')}")
    print(f"Age in commit log: {verify_in_commit_log('age', '25')}") 