#!/usr/bin/env python3
"""
Generate a secure Django SECRET_KEY.
Usage: python3 generate_secret_key.py
"""
from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    print(get_random_secret_key())
