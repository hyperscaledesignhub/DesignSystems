import json

def commit_log_write(key: str, value: str, filename: str = "commit.log") -> bool:
    """
    Write key-value pair to commit log.
    
    Args:
        key (str): The key to write
        value (str): The value to write
        filename (str): The commit log file to write to, defaults to "commit.log"
        
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

def commit_log_read(key: str, filename: str = "commit.log") -> str:
    """
    Read value for key from commit log.
    
    Args:
        key (str): The key to look up
        filename (str): The commit log file to read from, defaults to "commit.log"
        
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
    commit_log_write("name", "Alice")
    commit_log_write("age", "25")
    commit_log_write("name", "Bob")  # Update name
    
    print(f"Name: {commit_log_read('name')}")  # Should print "Bob"
    print(f"Age: {commit_log_read('age')}")    # Should print "25"
    print(f"City: {commit_log_read('city')}")  # Should print "None" 