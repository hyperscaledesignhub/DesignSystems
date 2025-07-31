import json

def sstable_write(key: str, value: str, filename: str = "sstable.data") -> bool:
    """
    Write key-value pair to SSTable.
    
    Args:
        key (str): The key to write
        value (str): The value to write
        filename (str): The SSTable file to write to, defaults to "sstable.data"
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    try:
        entry = {"key": key, "value": value}
        with open(filename, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return True
    except:
        return False

def sstable_read(key: str, filename: str = "sstable.data") -> str:
    """
    Read value for key from SSTable.
    
    Args:
        key (str): The key to look up
        filename (str): The SSTable file to read from, defaults to "sstable.data"
        
    Returns:
        str: The latest value for the key, or None if key not found
    """
    try:
        latest_value = None
        with open(filename, "r") as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry["key"] == key:
                    latest_value = entry["value"]
        return latest_value
    except:
        return None

if __name__ == "__main__":
    # Example usage
    sstable_write("name", "Alice")
    sstable_write("age", "25")
    sstable_write("name", "Bob")  # Update name
    
    print(f"Name: {sstable_read('name')}")  # Should print "Bob"
    print(f"Age: {sstable_read('age')}")    # Should print "25"
    print(f"City: {sstable_read('city')}")  # Should print "None" 