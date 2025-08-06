def add_numbers(x, y):
    """This function adds two numbers"""
    return x + y

def subtract_numbers(x, y):
    """This function subtracts two numbers"""
    return x - y

def multiply_numbers(x, y):
    """This function multiplies two numbers"""
    return x * y

if __name__ == "__main__":
    num1 = 20
    num2 = 10

    sum_result = add_numbers(num1, num2)
    print(f"The sum is: {sum_result}")

    product_result = multiply_numbers(num1, num2)
    print(f"The product is: {product_result}")