# fibonacci_iterative.py
# Calculates Fibonacci sequence using a loop

def calculate_fibonacci(limit):
    """
    Calculates Fibonacci numbers up to a certain limit using iteration.
    This approach is much more efficient.
    """
    a, b = 0, 1
    sequence = []
    while len(sequence) < limit:
        sequence.append(a)
        a, b = b, a + b
    return sequence

# Get the first 10 numbers
fib_numbers = calculate_fibonacci(10)
print("Fibonacci sequence (iterative):")
for index, num in enumerate(fib_numbers):
    print(f"F({index+1}) = {num}")