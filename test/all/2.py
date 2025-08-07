def sum_values(val1, val2):
    """This function sums two values"""
    return val1 + val2

def subtract_values(val1, val2):
    """This function gets the difference of two values"""
    return val1 - val2

def multiply_values(val1, val2):
    """This function gets the product of two values"""
    return val1 * val2

if __name__ == "__main__":
    first_num = 20
    second_num = 10

    addition_output = sum_values(first_num, second_num)
    print(f"The sum is: {addition_output}")

    multiplication_output = multiply_values(first_num, second_num)
    print(f"The product is: {multiplication_output}")