def fibonacci_iterative(n):
    """
    Generate the nth Fibonacci number using an iterative approach.
    
    Args:
        n (int): The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        int: The nth Fibonacci number
        
    Raises:
        TypeError: If n is not an integer
        ValueError: If n is negative
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    
    if n < 0:
        raise ValueError("Input must be a non-negative integer")
    
    if n == 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b


def fibonacci_recursive(n):
    """
    Generate the nth Fibonacci number using a recursive approach.
    
    Args:
        n (int): The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        int: The nth Fibonacci number
        
    Raises:
        TypeError: If n is not an integer
        ValueError: If n is negative
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    
    if n < 0:
        raise ValueError("Input must be a non-negative integer")
    
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_sequence_iterative(count):
    """
    Generate a sequence of Fibonacci numbers up to the given count using iterative approach.
    
    Args:
        count (int): Number of Fibonacci numbers to generate
        
    Returns:
        list: List containing the first 'count' Fibonacci numbers
        
    Raises:
        TypeError: If count is not an integer
        ValueError: If count is negative
    """
    if not isinstance(count, int):
        raise TypeError("Count must be an integer")
    
    if count < 0:
        raise ValueError("Count must be a non-negative integer")
    
    if count == 0:
        return []
    
    sequence = [0]
    if count > 1:
        sequence.append(1)
        
    for i in range(2, count):
        sequence.append(sequence[i-1] + sequence[i-2])
    
    return sequence


def fibonacci_sequence_recursive(count):
    """
    Generate a sequence of Fibonacci numbers up to the given count using recursive approach.
    
    Args:
        count (int): Number of Fibonacci numbers to generate
        
    Returns:
        list: List containing the first 'count' Fibonacci numbers
        
    Raises:
        TypeError: If count is not an integer
        ValueError: If count is negative
    """
    if not isinstance(count, int):
        raise TypeError("Count must be an integer")
    
    if count < 0:
        raise ValueError("Count must be a non-negative integer")
    
    def fib_helper(index):
        if index == 0:
            return 0
        elif index == 1:
            return 1
        else:
            return fib_helper(index - 1) + fib_helper(index - 2)
    
    if count == 0:
        return []
    
    return [fib_helper(i) for i in range(count)]
