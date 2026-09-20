"""Synthetic inventory: a method, an unrelated function, and a near variant."""
class TextTools:
    def tidy(self, text):
        return text.strip().lower()

def add_tax(amount, rate):
    return amount * (1 + rate)

def normalize_name(value):
    return value.strip().lower()
