from commit_log import commit_log_write, commit_log_read

def put(key: str, value: str) -> bool:
    """
    Store key-value pair in the key-value store.
    
    Args:
        key (str): The key to store
        value (str): The value to store
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return commit_log_write(key, value, "kvstore.log")
    except Exception:
        return False

def get(key: str) -> str:
    """
    Retrieve value for key from the key-value store.
    
    Args:
        key (str): The key to look up
        
    Returns:
        str: The value for the key, or None if key not found
    """
    try:
        return commit_log_read(key, "kvstore.log")
    except Exception:
        return None

if __name__ == "__main__":
    # Example usage
    # Store data
    put("name", "Alice")
    put("age", "25")
    put("name", "Bob")  # Update name
    
    # Retrieve data
    print(f"Name: {get('name')}")  # Should print "Bob"
    print(f"Age: {get('age')}")    # Should print "25"
    print(f"City: {get('city')}")  # Should print "None" 