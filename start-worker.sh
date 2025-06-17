#!/bin/bash

echo "Starting price checker worker..."
python3 -c "
import asyncio
from background import start_price_checker
asyncio.run(start_price_checker())
"