# Global cache storage: {namespace: {key: value}}
_cache_storage = {}

class CacheFullError(Exception):
    pass

def cache_put(key: str, value: str, max_size: int = 1000, namespace: str = "default") -> bool:
    """
    Store key-value pair in cache for a given namespace.
    
    Args:
        key (str): The key to store
        value (str): The value to store
        max_size (int): Maximum number of entries in cache, defaults to 1000
        namespace (str): The namespace for the cache, defaults to "default"
        
    Returns:
        bool: True if successful
        
    Raises:
        CacheFullError: If cache is full and key doesn't exist
    """
    global _cache_storage
    if namespace not in _cache_storage:
        _cache_storage[namespace] = {}
    cache = _cache_storage[namespace]
    if len(cache) >= max_size and key not in cache:
        raise CacheFullError(f"Cache memory is full for namespace '{namespace}'")
    cache[key] = value
    return True

def cache_get(key: str, namespace: str = "default") -> str:
    """
    Get value for key from cache for a given namespace.
    
    Args:
        key (str): The key to look up
        namespace (str): The namespace for the cache, defaults to "default"
        
    Returns:
        str: The value for the key, or None if key not found
    """
    global _cache_storage
    return _cache_storage.get(namespace, {}).get(key, None)

def cache_size(namespace: str = "default") -> int:
    """
    Return current number of entries in cache for a given namespace.
    
    Args:
        namespace (str): The namespace for the cache, defaults to "default"
        
    Returns:
        int: Number of entries in cache
    """
    global _cache_storage
    return len(_cache_storage.get(namespace, {}))

def cache_clear(namespace: str = "default") -> None:
    """
    Clear all entries from cache for a given namespace.
    
    Args:
        namespace (str): The namespace for the cache, defaults to "default"
    """
    global _cache_storage
    _cache_storage[namespace] = {}

def cache_keys(namespace: str = "default") -> list:
    """
    Return list of all keys in cache for a given namespace.
    
    Args:
        namespace (str): The namespace for the cache, defaults to "default"
        
    Returns:
        list: List of all keys in cache
    """
    global _cache_storage
    return list(_cache_storage.get(namespace, {}).keys())

if __name__ == "__main__":
    # Example usage
    try:
        # Store some data in cache
        cache_put("user:123", "john_doe")
        cache_put("user:456", "jane_smith") 
        cache_put("user:123", "john_smith")  # Update

        # Retrieve data from cache
        print(f"Name: {cache_get('user:123')}")  # Should print "john_smith"
        print(f"Name: {cache_get('user:456')}")  # Should print "jane_smith"
        print(f"Name: {cache_get('user:999')}")  # Should print "None"

        # Check cache status
        print(f"Cache size: {cache_size()}")  # Should print "2"
        print(f"Keys: {cache_keys()}")        # Should print "['user:123', 'user:456']"

        # Demonstrate cache full scenario
        print("\nFilling cache to limit...")
        for i in range(997):  # Already have 2 entries
            cache_put(f"key_{i}", f"value_{i}", max_size=1000)
        
        print(f"Cache size before full: {cache_size()}")  # Should print "999"
        
        # Next put will fail
        try:
            cache_put("new_key", "new_value", max_size=1000)
        except Exception as e:
            print(f"Error: {e}")  # Should print "Cache memory is full"

        # But updating existing key still works
        cache_put("key_0", "updated_value", max_size=1000)  # Success
        print(f"Updated value: {cache_get('key_0')}")  # Should print "updated_value"

    finally:
        # Clean up
        cache_clear() 