#!/usr/bin/python3


"""
Requires AWS credentials as environment variables
  AWS_SECRET_ACCESS_KEY=fakeSecretAccessKey
  AWS_ACCESS_KEY_ID=fakeMyKeyId
"""
import sys
import os
import logging

sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")

from jaguar.main import jaguar_production

if __name__ == "__main__":
    logging.basicConfig()
    jaguar_production()
