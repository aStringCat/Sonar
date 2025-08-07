# word_counter.py
# This script reads a text file and counts word frequency.

import re
from collections import Counter

def count_words(filepath):
    """Reads a file and returns a Counter object of word frequencies."""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            text = file.read().lower()
            # Use regex to find all words
            words = re.findall(r'\b\w+\b', text)
            return Counter(words)
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return None

# Create a dummy file for testing
with open("sample.txt", "w") as f:
    f.write("Hello world, this is a test. Hello again world!")

word_counts = count_words("sample.txt")
if word_counts:
    print("Most common words:")
    for word, count in word_counts.most_common(5):
        print(f"- {word}: {count}")