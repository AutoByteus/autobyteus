def generate_fibonacci(n: int) -> list:
    """
    Generate the first 'n' Fibonacci numbers using an iterative approach.

    Args:
        n (int): The number of Fibonacci terms to generate.

    Returns:
        list: A list containing the first 'n' Fibonacci numbers.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("Number of terms must be non-negative.")

    if n == 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    # Initialize the first two Fibonacci numbers
    fib_list = [0, 1]

    # Generate the rest iteratively
    for i in range(2, n):
        next_fib = fib_list[i - 1] + fib_list[i - 2]
        fib_list.append(next_fib)

    return fib_list

# Example usage:
# print(generate_fibonacci(10))  # Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]