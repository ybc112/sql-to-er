#!/bin/bash
cd /root/sql4/sql_to_er/web_app
echo "Starting Flask app from: $(pwd)"
echo "Templates directory: $(ls templates/)"
python3 app.py