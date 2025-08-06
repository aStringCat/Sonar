# fibonacci_recursive.py
# Calculates Fibonacci sequence using recursion

def fibonacci(n):
    """
    Calculates the n-th Fibonacci number using recursion.
    Warning: This is inefficient for large n.
    """
    if n <= 0:
        print("Input should be a positive integer.")
        return None
    elif n == 1:
        return 0
    elif n == 2:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)

# Print the first 10 numbers of the sequence
print("Fibonacci sequence (recursive):")
for i in range(1, 11):
    print(f"F({i}) = {fibonacci(i+1)}")